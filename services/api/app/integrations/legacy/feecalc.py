"""Python reference implementation of the COBOL batch program ``FEECALC01``.

``FEECALC01`` (``legacy/cobol/FEECALC01.cbl``, tariff in
``legacy/cobol/copybooks/FEESCHED.cpy``) prices outbound WIRE and SWIFT
payments. The modern fee service delegates the legacy-governed rails
(``WIRE_USD`` and ``SWIFT_INTL``) to :func:`calculate_wire_fee` so that the
Python platform produces the exact same fee the mainframe batch produced.
Parity is enforced by the golden-master tests in ``legacy/reference-tests``.

Paragraph map (COBOL paragraph -> Python step)
----------------------------------------------
``2050-VALIDATE-INPUT``
    Amount must be numeric and fit ``PIC 9(13)V99`` (status ``03``); segment
    must be ``I``/``C``/``R`` (status ``01``); rail must be ``WIRE`` or
    ``SWIFT`` (status ``02``). Mirrored by :func:`_validate_amount`,
    :func:`normalize_segment_code` and :func:`normalize_rail_code`; failures
    raise :class:`FeeCalcInputError` carrying the same status code.
``2100-SELECT-BAND``
    First band in ascending order whose *inclusive* upper bound is >= the
    amount. :func:`select_band`.
``2200-COMPUTE-BANDED-FEE``
    ``bps_component = ROUNDED(amount * rate)`` to 2 dp, then
    ``banded_fee = base_fee + bps_component``.
``2300-APPLY-CAP``
    ``capped_fee = min(banded_fee, FEE_CAP)``; the flag is set only on a
    strict ``banded_fee > FEE_CAP``.
``2400-APPLY-SEGMENT``
    ``segment_fee = ROUNDED(capped_fee * multiplier)`` to 2 dp.
``2500-APPLY-RAIL-SURCHARGE``
    ``fee = segment_fee + surcharge``; the surcharge is never capped.

Rounding
--------
Every ``COMPUTE ... ROUNDED`` in the COBOL uses the GnuCOBOL default mode
``NEAREST-AWAY-FROM-ZERO``, which for non-negative values is identical to
``decimal.ROUND_HALF_UP``. Intermediate products are exact in both
implementations (GnuCOBOL uses arbitrary-precision decimals internally; the
scaled rates have at most six decimals), so the only rounding points are the
two shown above.

Record layouts
--------------
The fixed-width ``FEEIN``/``FEEOUT`` layouts are part of the program's
contract and are encoded here too (:func:`encode_feein_record`,
:func:`parse_feeout_record`) so that the golden tests and
``legacy/cobol/run_fixtures.sh`` share a single definition.

This module is intentionally self-contained (standard library only) so it can
be imported by tests, scripts and services without pulling in the ORM or the
web framework.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

__all__ = [
    "FEEIN_RECORD_LENGTH",
    "FEEOUT_RECORD_LENGTH",
    "FEESCHED_VERSION",
    "FEE_BANDS",
    "FEE_CAP",
    "LEGACY_RAIL_CODES",
    "LEGACY_SEGMENT_CODES",
    "MAX_AMOUNT",
    "RAIL_SWIFT",
    "RAIL_WIRE",
    "SEGMENT_CORPORATE",
    "SEGMENT_INSTITUTIONAL",
    "SEGMENT_MULTIPLIERS",
    "SEGMENT_RETAIL",
    "SWIFT_SURCHARGE",
    "FeeBand",
    "FeeCalcInputError",
    "FeeCalcResult",
    "FeeOutRecord",
    "calculate_wire_fee",
    "encode_feein_record",
    "legacy_segment_code",
    "normalize_rail_code",
    "normalize_segment_code",
    "parse_feeout_record",
    "select_band",
]

# --------------------------------------------------------------------------- #
# Tariff (mirrors FEESCHED.cpy exactly)
# --------------------------------------------------------------------------- #

FEESCHED_VERSION: Final[str] = "2026.03.01"

_CENT: Final[Decimal] = Decimal("0.01")
_ZERO: Final[Decimal] = Decimal("0.00")

#: Largest value representable in the ``PIC 9(13)V99`` amount field.
MAX_AMOUNT: Final[Decimal] = Decimal("9999999999999.99")


@dataclass(frozen=True, slots=True)
class FeeBand:
    """One row of the FEESCHED band table."""

    number: int
    upper_bound: Decimal
    """Inclusive upper bound; band 4 carries the field maximum as a sentinel."""
    base_fee: Decimal
    bps_rate: Decimal
    """Scaled decimal rate exactly as stored in ``PIC V9(6)`` (1.0 bps = 0.000100)."""
    label: str

    def contains(self, amount: Decimal) -> bool:
        return amount <= self.upper_bound


FEE_BANDS: Final[tuple[FeeBand, ...]] = (
    FeeBand(1, Decimal("10000.00"), Decimal("15.00"), Decimal("0.000000"), "<= 10,000.00"),
    FeeBand(2, Decimal("100000.00"), Decimal("25.00"), Decimal("0.000100"), "<= 100,000.00"),
    FeeBand(3, Decimal("1000000.00"), Decimal("35.00"), Decimal("0.000050"), "<= 1,000,000.00"),
    FeeBand(4, MAX_AMOUNT, Decimal("50.00"), Decimal("0.000025"), "> 1,000,000.00"),
)

#: ``FS-FEE-CAP`` - applies to the banded fee only.
FEE_CAP: Final[Decimal] = Decimal("250.00")

#: ``FS-SWIFT-SURCHARGE`` - added after the multiplier, never capped.
SWIFT_SURCHARGE: Final[Decimal] = Decimal("12.00")

SEGMENT_INSTITUTIONAL: Final[str] = "I"
SEGMENT_CORPORATE: Final[str] = "C"
SEGMENT_RETAIL: Final[str] = "R"

#: ``FEESCHED-SEGMENT-RATES`` keyed by the one-character legacy segment code.
SEGMENT_MULTIPLIERS: Final[Mapping[str, Decimal]] = {
    SEGMENT_INSTITUTIONAL: Decimal("0.80"),
    SEGMENT_CORPORATE: Decimal("1.00"),
    SEGMENT_RETAIL: Decimal("1.10"),
}
LEGACY_SEGMENT_CODES: Final[frozenset[str]] = frozenset(SEGMENT_MULTIPLIERS)

RAIL_WIRE: Final[str] = "WIRE"
RAIL_SWIFT: Final[str] = "SWIFT"
LEGACY_RAIL_CODES: Final[frozenset[str]] = frozenset({RAIL_WIRE, RAIL_SWIFT})

_RAIL_SURCHARGES: Final[Mapping[str, Decimal]] = {
    RAIL_WIRE: _ZERO,
    RAIL_SWIFT: SWIFT_SURCHARGE,
}

# Spellings accepted on input and folded to the canonical legacy code.  The
# COBOL accepts 'WIRE ' and the underscore-padded alias 'WIRE_'; the modern
# rail enum values are accepted here so callers can pass ``Rail.value``.
_RAIL_ALIASES: Final[Mapping[str, str]] = {
    "WIRE": RAIL_WIRE,
    "WIRE_": RAIL_WIRE,
    "WIRE_USD": RAIL_WIRE,
    "SWIFT": RAIL_SWIFT,
    "SWIFT_INTL": RAIL_SWIFT,
}

# Modern ``CustomerSegment`` names folded to the legacy one-character code.
# INTERNAL (the bank's own treasury) has no code in the 1990s tariff; the
# mainframe priced internal-book movements through the corporate schedule,
# which is what the modern service continues to do for legacy-governed rails.
_SEGMENT_ALIASES: Final[Mapping[str, str]] = {
    "I": SEGMENT_INSTITUTIONAL,
    "C": SEGMENT_CORPORATE,
    "R": SEGMENT_RETAIL,
    "INSTITUTIONAL": SEGMENT_INSTITUTIONAL,
    "CORPORATE": SEGMENT_CORPORATE,
    "RETAIL": SEGMENT_RETAIL,
    "INTERNAL": SEGMENT_CORPORATE,
}

# --------------------------------------------------------------------------- #
# Errors and results
# --------------------------------------------------------------------------- #


class FeeCalcInputError(ValueError):
    """Input rejected by ``2050-VALIDATE-INPUT``.

    ``status_code`` is the two-character status FEECALC01 writes in columns
    33-34 of the FEEOUT record: ``01`` bad segment, ``02`` bad rail, ``03``
    amount not numeric / out of range.
    """

    STATUS_BAD_SEGMENT: Final[str] = "01"
    STATUS_BAD_RAIL: Final[str] = "02"
    STATUS_BAD_AMOUNT: Final[str] = "03"

    def __init__(self, status_code: str, message: str) -> None:
        super().__init__(f"FEECALC01 status {status_code}: {message}")
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class FeeCalcResult:
    """Full breakdown of one FEECALC01 pricing, every amount at 2 dp."""

    fee: Decimal
    band: int
    base_fee: Decimal
    bps_component: Decimal
    multiplier: Decimal
    surcharge: Decimal
    capped: bool
    banded_fee: Decimal
    """``base_fee + bps_component`` before the cap (``WS-BANDED-FEE``)."""
    segment_code: str
    rail_code: str

    @property
    def capped_fee(self) -> Decimal:
        """``WS-CAPPED-FEE``: the banded fee after the cap, before the multiplier."""
        return FEE_CAP if self.capped else self.banded_fee

    def as_breakdown(self) -> dict[str, str]:
        """Serializable breakdown; amounts as strings per the API money contract."""
        return {
            "program": "FEECALC01",
            "schedule_version": FEESCHED_VERSION,
            "band": str(self.band),
            "base_fee": f"{self.base_fee:.2f}",
            "bps_component": f"{self.bps_component:.2f}",
            "banded_fee": f"{self.banded_fee:.2f}",
            "capped": "true" if self.capped else "false",
            "capped_fee": f"{self.capped_fee:.2f}",
            "segment_code": self.segment_code,
            "multiplier": f"{self.multiplier:.2f}",
            "rail_code": self.rail_code,
            "surcharge": f"{self.surcharge:.2f}",
            "fee": f"{self.fee:.2f}",
        }


# --------------------------------------------------------------------------- #
# Normalization (2050-VALIDATE-INPUT)
# --------------------------------------------------------------------------- #


def normalize_segment_code(segment_code: str) -> str:
    """Return the legacy ``I``/``C``/``R`` code for a code or ``CustomerSegment`` name.

    Raises :class:`FeeCalcInputError` (status ``01``) for anything else, as
    ``2050-VALIDATE-INPUT`` does for an unknown segment byte.
    """
    key = segment_code.strip().upper()
    try:
        return _SEGMENT_ALIASES[key]
    except KeyError:
        raise FeeCalcInputError(
            FeeCalcInputError.STATUS_BAD_SEGMENT,
            f"segment code {segment_code!r} is not one of I/C/R",
        ) from None


def legacy_segment_code(segment: str) -> str:
    """Alias of :func:`normalize_segment_code` for callers holding a segment enum value."""
    return normalize_segment_code(segment)


def normalize_rail_code(rail_code: str) -> str:
    """Return ``WIRE`` or ``SWIFT`` for a legacy rail field or a modern ``Rail`` value.

    Raises :class:`FeeCalcInputError` (status ``02``) for rails FEECALC01 does
    not price (ACH, SEPA, CHAPS, internal book).
    """
    key = rail_code.strip().upper()
    try:
        return _RAIL_ALIASES[key]
    except KeyError:
        raise FeeCalcInputError(
            FeeCalcInputError.STATUS_BAD_RAIL,
            f"rail code {rail_code!r} is not priced by FEECALC01 (WIRE/SWIFT only)",
        ) from None


def _require_decimal(value: object, name: str) -> Decimal:
    """Reject anything that is not a ``Decimal`` - in particular ``float`` (see docs: money)."""
    if not isinstance(value, Decimal):
        raise TypeError(
            f"{name} must be a decimal.Decimal, got {type(value).__name__}; "
            "floats are never accepted for money"
        )
    return value


def _validate_amount(value: Decimal) -> Decimal:
    """Return ``value`` quantized to cents after the ``PIC 9(13)V99`` checks."""
    amount = _require_decimal(value, "amount")
    if not amount.is_finite():
        raise FeeCalcInputError(FeeCalcInputError.STATUS_BAD_AMOUNT, "amount is not numeric")
    if amount < 0:
        raise FeeCalcInputError(
            FeeCalcInputError.STATUS_BAD_AMOUNT, "amount field is unsigned; negative not allowed"
        )
    if amount > MAX_AMOUNT:
        raise FeeCalcInputError(
            FeeCalcInputError.STATUS_BAD_AMOUNT, f"amount exceeds PIC 9(13)V99 maximum {MAX_AMOUNT}"
        )
    cents = amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    if cents != amount:
        raise FeeCalcInputError(
            FeeCalcInputError.STATUS_BAD_AMOUNT,
            f"amount {amount} has more than two decimal places",
        )
    return cents


# --------------------------------------------------------------------------- #
# Calculation (2100 .. 2500)
# --------------------------------------------------------------------------- #


def select_band(amount: Decimal) -> FeeBand:
    """``2100-SELECT-BAND``: first band whose inclusive upper bound is >= amount."""
    for band in FEE_BANDS:
        if band.contains(amount):
            return band
    # Unreachable for validated input: band 4's bound is the field maximum.
    raise FeeCalcInputError(
        FeeCalcInputError.STATUS_BAD_AMOUNT, f"amount {amount} exceeds the band table"
    )


def _round_cents(value: Decimal) -> Decimal:
    """``COMPUTE ... ROUNDED`` under NEAREST-AWAY-FROM-ZERO for non-negative values."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def calculate_wire_fee(amount: Decimal, segment_code: str, rail_code: str) -> FeeCalcResult:
    """Price one payment exactly as ``FEECALC01`` does.

    :param amount: payment amount in the payment currency, ``Decimal`` with at
        most two decimal places, ``0 <= amount <= 9,999,999,999,999.99``.
    :param segment_code: ``I``/``C``/``R`` or a ``CustomerSegment`` name.
    :param rail_code: ``WIRE``/``SWIFT`` (legacy) or ``WIRE_USD``/``SWIFT_INTL``.
    :raises FeeCalcInputError: for inputs FEECALC01 would reject.
    :raises TypeError: if ``amount`` is not a ``Decimal`` (floats are refused).
    """
    # 2050-VALIDATE-INPUT (same order as the COBOL: amount, segment, rail)
    cents = _validate_amount(amount)
    segment = normalize_segment_code(segment_code)
    rail = normalize_rail_code(rail_code)
    multiplier = SEGMENT_MULTIPLIERS[segment]
    surcharge = _RAIL_SURCHARGES[rail]

    # 2100-SELECT-BAND
    band = select_band(cents)

    # 2200-COMPUTE-BANDED-FEE
    bps_component = _round_cents(cents * band.bps_rate)
    banded_fee = band.base_fee + bps_component

    # 2300-APPLY-CAP
    capped = banded_fee > FEE_CAP
    capped_fee = FEE_CAP if capped else banded_fee

    # 2400-APPLY-SEGMENT
    segment_fee = _round_cents(capped_fee * multiplier)

    # 2500-APPLY-RAIL-SURCHARGE
    fee = segment_fee + surcharge

    return FeeCalcResult(
        fee=fee,
        band=band.number,
        base_fee=band.base_fee,
        bps_component=bps_component,
        multiplier=multiplier,
        surcharge=surcharge,
        capped=capped,
        banded_fee=banded_fee,
        segment_code=segment,
        rail_code=rail,
    )


# --------------------------------------------------------------------------- #
# FEEIN / FEEOUT record layouts
# --------------------------------------------------------------------------- #

#: ``FEEIN-RECORD PIC X(21)``: amount 9(13)V99 | segment X | rail X(5)
FEEIN_RECORD_LENGTH: Final[int] = 21
#: ``FEEOUT-RECORD PIC X(34)``: echo X(21) | fee 9(7)V99 | band 9 | cap X | status XX
FEEOUT_RECORD_LENGTH: Final[int] = 34

_AMOUNT_WIDTH: Final[int] = 15
_FEE_WIDTH: Final[int] = 9


def encode_feein_record(amount: Decimal, segment_code: str, rail_code: str) -> str:
    """Build one 21-byte FEEIN record (no newline) for the COBOL program.

    The amount is written as fifteen plain digits with two implied decimals,
    the segment as its single legacy code and the rail left-justified in five
    bytes (``'WIRE '`` / ``'SWIFT'``). Inputs are normalized the same way
    :func:`calculate_wire_fee` normalizes them.
    """
    cents = _validate_amount(amount)
    segment = normalize_segment_code(segment_code)
    rail = normalize_rail_code(rail_code)
    scaled = int((cents * 100).to_integral_value())
    record = f"{scaled:0{_AMOUNT_WIDTH}d}{segment}{rail:<5}"
    if len(record) != FEEIN_RECORD_LENGTH:  # pragma: no cover - guarded by validation
        raise AssertionError(f"FEEIN record has length {len(record)}, expected 21")
    return record


@dataclass(frozen=True, slots=True)
class FeeOutRecord:
    """Parsed FEEOUT line."""

    amount: Decimal
    segment_code: str
    rail_code: str
    fee: Decimal
    band: int
    capped: bool
    status_code: str

    @property
    def ok(self) -> bool:
        return self.status_code == "00"


def parse_feeout_record(line: str) -> FeeOutRecord:
    """Parse one FEEOUT line written by FEECALC01 (trailing newline tolerated)."""
    raw = line.rstrip("\r\n")
    if len(raw) != FEEOUT_RECORD_LENGTH:
        raise ValueError(
            f"FEEOUT record has length {len(raw)}, expected {FEEOUT_RECORD_LENGTH}: {raw!r}"
        )
    amount_digits = raw[0:_AMOUNT_WIDTH]
    segment = raw[15]
    rail = raw[16:21].rstrip(" _")
    fee_digits = raw[21 : 21 + _FEE_WIDTH]
    band = int(raw[30])
    cap_flag = raw[31]
    status = raw[32:34]
    if not fee_digits.isdigit():
        raise ValueError(f"FEEOUT fee field is not numeric: {fee_digits!r}")
    amount = (
        Decimal(int(amount_digits)).scaleb(-2).quantize(_CENT)
        if amount_digits.isdigit()
        else Decimal("NaN")
    )
    return FeeOutRecord(
        amount=amount,
        segment_code=segment,
        rail_code=rail,
        fee=Decimal(int(fee_digits)).scaleb(-2).quantize(_CENT),
        band=band,
        capped=cap_flag == "Y",
        status_code=status,
    )
