"""Fee quotation.

``WIRE_USD`` and ``SWIFT_INTL`` are priced by the COBOL reference
(:func:`calculate_wire_fee`). Every other rail uses the modern tariff below,
which is also written into ``fee_schedules`` for the Policies page. The table
does not price legacy rails; those rows are display-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from app.domain.money.currency import quantize
from app.domain.money.rounding import apply_basis_points, to_decimal
from app.integrations.legacy.feecalc import calculate_wire_fee
from app.models.enums import Currency, CustomerSegment, FeeSource, FeeType, Rail

LEGACY_RAILS: Final[frozenset[Rail]] = frozenset({Rail.WIRE_USD, Rail.SWIFT_INTL})


@dataclass(frozen=True, slots=True)
class ModernTariff:
    rail: Rail
    currency: Currency
    segment: CustomerSegment
    fee_type: FeeType
    flat_amount: Decimal
    bps: int
    min_fee: Decimal
    max_fee: Decimal | None


@dataclass(frozen=True, slots=True)
class FeeQuote:
    amount: Decimal
    currency: Currency
    source: FeeSource
    breakdown: dict[str, str]


def _tariff(
    rail: Rail,
    currency: Currency,
    segment: CustomerSegment,
    fee_type: FeeType,
    flat: str,
    bps: int,
    minimum: str,
    maximum: str | None,
) -> ModernTariff:
    return ModernTariff(
        rail=rail,
        currency=currency,
        segment=segment,
        fee_type=fee_type,
        flat_amount=Decimal(flat),
        bps=bps,
        min_fee=Decimal(minimum),
        max_fee=Decimal(maximum) if maximum is not None else None,
    )


# Display and pricing source for non-legacy rails. INTERNAL is priced as CORPORATE.
MODERN_TARIFF: Final[tuple[ModernTariff, ...]] = (
    _tariff(
        Rail.ACH_USD, Currency.USD, CustomerSegment.RETAIL, FeeType.FLAT, "0.50", 0, "0.50", None
    ),
    _tariff(
        Rail.ACH_USD, Currency.USD, CustomerSegment.CORPORATE, FeeType.FLAT, "0.25", 0, "0.25", None
    ),
    _tariff(
        Rail.ACH_USD,
        Currency.USD,
        CustomerSegment.INSTITUTIONAL,
        FeeType.FLAT,
        "0.15",
        0,
        "0.15",
        None,
    ),
    _tariff(
        Rail.SEPA_EUR,
        Currency.EUR,
        CustomerSegment.RETAIL,
        FeeType.FLAT_PLUS_BPS,
        "1.00",
        3,
        "1.00",
        "15.00",
    ),
    _tariff(
        Rail.SEPA_EUR,
        Currency.EUR,
        CustomerSegment.CORPORATE,
        FeeType.FLAT_PLUS_BPS,
        "1.50",
        2,
        "1.50",
        "25.00",
    ),
    _tariff(
        Rail.SEPA_EUR,
        Currency.EUR,
        CustomerSegment.INSTITUTIONAL,
        FeeType.FLAT_PLUS_BPS,
        "2.00",
        1,
        "2.00",
        "40.00",
    ),
    _tariff(
        Rail.CHAPS_GBP,
        Currency.GBP,
        CustomerSegment.CORPORATE,
        FeeType.FLAT_PLUS_BPS,
        "4.00",
        2,
        "4.00",
        "40.00",
    ),
    _tariff(
        Rail.CHAPS_GBP,
        Currency.GBP,
        CustomerSegment.INSTITUTIONAL,
        FeeType.FLAT_PLUS_BPS,
        "6.00",
        1,
        "6.00",
        "50.00",
    ),
    _tariff(
        Rail.CHAPS_GBP,
        Currency.GBP,
        CustomerSegment.RETAIL,
        FeeType.FLAT,
        "8.00",
        0,
        "8.00",
        None,
    ),
    _tariff(
        Rail.INTERNAL_BOOK,
        Currency.USD,
        CustomerSegment.CORPORATE,
        FeeType.FLAT,
        "0.00",
        0,
        "0.00",
        None,
    ),
    _tariff(
        Rail.INTERNAL_BOOK,
        Currency.EUR,
        CustomerSegment.CORPORATE,
        FeeType.FLAT,
        "0.00",
        0,
        "0.00",
        None,
    ),
    _tariff(
        Rail.INTERNAL_BOOK,
        Currency.GBP,
        CustomerSegment.CORPORATE,
        FeeType.FLAT,
        "0.00",
        0,
        "0.00",
        None,
    ),
)

# Display-only rows for the legacy tariff. Pricing ignores them.
LEGACY_DISPLAY_TARIFF: Final[tuple[ModernTariff, ...]] = (
    _tariff(
        Rail.WIRE_USD,
        Currency.USD,
        CustomerSegment.INSTITUTIONAL,
        FeeType.FLAT_PLUS_BPS,
        "35.00",
        1,
        "0.00",
        None,
    ),
    _tariff(
        Rail.WIRE_USD,
        Currency.USD,
        CustomerSegment.CORPORATE,
        FeeType.FLAT_PLUS_BPS,
        "35.00",
        1,
        "0.00",
        None,
    ),
    _tariff(
        Rail.SWIFT_INTL,
        Currency.USD,
        CustomerSegment.CORPORATE,
        FeeType.FLAT_PLUS_BPS,
        "35.00",
        1,
        "0.00",
        None,
    ),
    _tariff(
        Rail.SWIFT_INTL,
        Currency.EUR,
        CustomerSegment.INSTITUTIONAL,
        FeeType.FLAT_PLUS_BPS,
        "35.00",
        1,
        "0.00",
        None,
    ),
)


def _pricing_segment(segment: CustomerSegment | str) -> CustomerSegment:
    value = segment if isinstance(segment, CustomerSegment) else CustomerSegment(str(segment))
    if value is CustomerSegment.INTERNAL:
        return CustomerSegment.CORPORATE
    return value


def lookup_modern_tariff(
    rail: Rail | str, currency: Currency | str, segment: CustomerSegment | str
) -> ModernTariff:
    """Return the modern tariff row for a non-legacy rail. Raises ``LookupError`` if none."""
    rail_value = rail if isinstance(rail, Rail) else Rail(rail)
    currency_value = currency if isinstance(currency, Currency) else Currency(currency)
    segment_value = _pricing_segment(segment)
    for row in MODERN_TARIFF:
        if (
            row.rail is rail_value
            and row.currency is currency_value
            and row.segment is segment_value
        ):
            return row
    # Currency-agnostic book transfers fall back to the USD corporate row of the same rail.
    for row in MODERN_TARIFF:
        if row.rail is rail_value and row.segment is segment_value:
            return row
    raise LookupError(
        f"No modern fee tariff for {rail_value.value}/{currency_value.value}/{segment_value.value}"
    )


def _quote_modern(amount: Decimal, currency: Currency, tariff: ModernTariff) -> FeeQuote:
    places = 0 if currency is Currency.JPY else 2
    fee = tariff.flat_amount + apply_basis_points(amount, tariff.bps, places)
    if fee < tariff.min_fee:
        fee = tariff.min_fee
    if tariff.max_fee is not None and fee > tariff.max_fee:
        fee = tariff.max_fee
    fee = quantize(fee, currency)
    return FeeQuote(
        amount=fee,
        currency=currency,
        source=FeeSource.MODERN,
        breakdown={
            "flat_amount": format(tariff.flat_amount, "f"),
            "bps": str(tariff.bps),
            "min_fee": format(tariff.min_fee, "f"),
            "max_fee": format(tariff.max_fee, "f") if tariff.max_fee is not None else "",
            "fee": format(fee, "f"),
        },
    )


def compute_fee(
    rail: Rail | str,
    currency: Currency | str,
    segment: CustomerSegment | str,
    amount: Decimal,
) -> FeeQuote:
    """Price one payment. Legacy rails delegate to ``FEECALC01``; others use the modern tariff."""
    principal = to_decimal(amount)
    rail_value = rail if isinstance(rail, Rail) else Rail(str(rail))
    currency_value = currency if isinstance(currency, Currency) else Currency(str(currency))
    segment_value = (
        segment if isinstance(segment, CustomerSegment) else CustomerSegment(str(segment))
    )
    if rail_value in LEGACY_RAILS:
        result = calculate_wire_fee(principal, segment_value.value, rail_value.value)
        return FeeQuote(
            amount=result.fee,
            currency=currency_value,
            source=FeeSource.LEGACY_FEECALC01,
            breakdown=result.as_breakdown(),
        )
    return _quote_modern(
        principal, currency_value, lookup_modern_tariff(rail_value, currency_value, segment_value)
    )
