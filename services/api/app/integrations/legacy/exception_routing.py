"""Python reference implementation of the VB6 module ``modExceptionRouting``.

The Payments Review Desk (a retired Visual Basic 6 client, source preserved in
``legacy/vb6/modExceptionRouting.bas``) decided which review queue a held
payment went to, how severe the exception was, and whether a supervisor had to
sign off. ``domain/exceptions/classification.py`` calls :func:`route_exception`
so the modern platform assigns the same ``queue`` and initial severity the desk
did. VB6 cannot be compiled on the build machines, so parity is guarded by the
fixtures in ``legacy/reference-tests/fixtures/exception_routing_cases.json``
and by a static comparison of this module's tables against the ``.bas`` source.

Behaviour (``Public Function RouteException`` in the ``.bas``)
---------------------------------------------------------------
1. Reason code and segment are trimmed and upper-cased.
2. Severity comes from the per-code table (``SeverityForReason``); an unknown
   code is treated as medium (``SEV_MEDIUM``), which is the ``Case Else`` of
   the VB6 ``Select Case``.
3. Queue:
   * ``R07`` (screening hit) -> ``FCR-SCREEN``, severity forced to 4,
     supervisor always required - evaluated before anything else;
   * segment ``I`` with amount >= 250,000 USD -> ``INST-HV``;
   * segment ``R`` -> ``RETAIL-STD``;
   * everything else (``C``, institutional below the threshold, unknown
     segment) -> ``CORP-STD`` (the VB6 ``Case Else``).
4. Supervisor required when severity >= 3 or amount >= 100,000 USD.

Legacy reason codes
-------------------
``R01`` INVALID ACCT, ``R02`` MISSING BIC, ``R03`` NAME MISMATCH, ``R04``
DUPLICATE, ``R05`` LIMIT, ``R06`` CUTOFF, ``R07`` SCREENING, ``R08`` NSF,
``R09`` STALE DATE, ``R10`` PURPOSE, ``R11`` CCY/RAIL. :data:`LEGACY_REASON_MAP`
maps them to the modern ``reason_code`` strings in
``domain/policies/exception_reasons.json`` and :func:`route_exception` accepts
either spelling.

This module is intentionally self-contained (standard library only).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Final

__all__ = [
    "DEFAULT_SEVERITY_UNKNOWN_REASON",
    "HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD",
    "LEGACY_REASON_MAP",
    "LEGACY_REASON_SEVERITY",
    "LEGACY_REASON_TITLES",
    "MODERN_REASON_MAP",
    "QUEUES",
    "QUEUE_CORP_STD",
    "QUEUE_FCR_SCREEN",
    "QUEUE_INST_HV",
    "QUEUE_RETAIL_STD",
    "REASON_SCREENING",
    "SEVERITY_CRITICAL",
    "SEVERITY_HIGH",
    "SEVERITY_LABELS",
    "SEVERITY_LOW",
    "SEVERITY_MEDIUM",
    "SUPERVISOR_AMOUNT_THRESHOLD_USD",
    "SUPERVISOR_SEVERITY_THRESHOLD",
    "RoutingResult",
    "normalize_reason_code",
    "normalize_segment",
    "route_exception",
    "to_legacy_reason",
    "to_modern_reason",
]

# --------------------------------------------------------------------------- #
# Constants (mirror the Public Const block of modExceptionRouting.bas)
# --------------------------------------------------------------------------- #

QUEUE_RETAIL_STD: Final[str] = "RETAIL-STD"
QUEUE_CORP_STD: Final[str] = "CORP-STD"
QUEUE_INST_HV: Final[str] = "INST-HV"
QUEUE_FCR_SCREEN: Final[str] = "FCR-SCREEN"
QUEUES: Final[frozenset[str]] = frozenset(
    {QUEUE_RETAIL_STD, QUEUE_CORP_STD, QUEUE_INST_HV, QUEUE_FCR_SCREEN}
)

SEVERITY_LOW: Final[int] = 1
SEVERITY_MEDIUM: Final[int] = 2
SEVERITY_HIGH: Final[int] = 3
SEVERITY_CRITICAL: Final[int] = 4

#: Numeric VB6 severity -> modern ``ExceptionSeverity`` name.
SEVERITY_LABELS: Final[Mapping[int, str]] = MappingProxyType(
    {
        SEVERITY_LOW: "LOW",
        SEVERITY_MEDIUM: "MEDIUM",
        SEVERITY_HIGH: "HIGH",
        SEVERITY_CRITICAL: "CRITICAL",
    }
)

#: ``HV_AMOUNT_THRESHOLD``: institutional payments at or above this go to INST-HV.
HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD: Final[Decimal] = Decimal("250000.00")
#: ``SUPERVISOR_AMOUNT_THRESHOLD``: at or above this a supervisor must sign off.
SUPERVISOR_AMOUNT_THRESHOLD_USD: Final[Decimal] = Decimal("100000.00")
#: ``SUPERVISOR_SEVERITY_THRESHOLD``: at or above this a supervisor must sign off.
SUPERVISOR_SEVERITY_THRESHOLD: Final[int] = SEVERITY_HIGH

REASON_SCREENING: Final[str] = "R07"

#: Severity table (``SeverityForReason``). Unknown codes fall back to MEDIUM.
LEGACY_REASON_SEVERITY: Final[Mapping[str, int]] = MappingProxyType(
    {
        "R01": SEVERITY_HIGH,
        "R02": SEVERITY_MEDIUM,
        "R03": SEVERITY_HIGH,
        "R04": SEVERITY_HIGH,
        "R05": SEVERITY_HIGH,
        "R06": SEVERITY_MEDIUM,
        "R07": SEVERITY_CRITICAL,
        "R08": SEVERITY_MEDIUM,
        "R09": SEVERITY_LOW,
        "R10": SEVERITY_MEDIUM,
        "R11": SEVERITY_HIGH,
    }
)
DEFAULT_SEVERITY_UNKNOWN_REASON: Final[int] = SEVERITY_MEDIUM

#: Short descriptions as they appeared in the VB6 reason combo box.
LEGACY_REASON_TITLES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "R01": "INVALID ACCT",
        "R02": "MISSING BIC",
        "R03": "NAME MISMATCH",
        "R04": "DUPLICATE",
        "R05": "LIMIT",
        "R06": "CUTOFF",
        "R07": "SCREENING",
        "R08": "NSF",
        "R09": "STALE DATE",
        "R10": "PURPOSE",
        "R11": "CCY/RAIL",
    }
)

#: Legacy ``Rnn`` code -> modern ``reason_code`` (exception_reasons.json).
LEGACY_REASON_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {
        "R01": "INVALID_ACCOUNT_IDENTIFIER",
        "R02": "MISSING_BENEFICIARY_BIC",
        "R03": "BENEFICIARY_NAME_MISMATCH",
        "R04": "DUPLICATE_REFERENCE",
        "R05": "AMOUNT_LIMIT_EXCEEDED",
        "R06": "CUTOFF_MISSED",
        "R07": "SCREENING_REVIEW",
        "R08": "INSUFFICIENT_FUNDS",
        "R09": "STALE_VALUE_DATE",
        "R10": "MISSING_PURPOSE_CODE",
        "R11": "UNSUPPORTED_CURRENCY_RAIL",
    }
)

#: Modern ``reason_code`` -> legacy ``Rnn`` code (inverse of LEGACY_REASON_MAP).
MODERN_REASON_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {modern: legacy for legacy, modern in LEGACY_REASON_MAP.items()}
)

# Modern ``CustomerSegment`` names folded to the one-character desk code.
# INTERNAL has no desk code; it falls to the VB6 ``Case Else`` (CORP-STD),
# which is also where the fee tariff prices it.
_SEGMENT_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "I": "I",
        "C": "C",
        "R": "R",
        "INSTITUTIONAL": "I",
        "CORPORATE": "C",
        "RETAIL": "R",
        "INTERNAL": "C",
    }
)

# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RoutingResult:
    """Mirror of the VB6 ``Public Type RoutingResult``."""

    queue: str
    severity: int
    requires_supervisor: bool
    legacy_reason_code: str | None
    """``R01``..``R11`` when the reason is known to the desk, else ``None``."""

    @property
    def severity_label(self) -> str:
        """Modern ``ExceptionSeverity`` name for :attr:`severity`."""
        return SEVERITY_LABELS[self.severity]

    @property
    def modern_reason_code(self) -> str | None:
        return to_modern_reason(self.legacy_reason_code) if self.legacy_reason_code else None


# --------------------------------------------------------------------------- #
# Code mapping helpers
# --------------------------------------------------------------------------- #


def to_modern_reason(legacy_code: str) -> str | None:
    """``R03`` -> ``BENEFICIARY_NAME_MISMATCH``; ``None`` when the code is unknown."""
    return LEGACY_REASON_MAP.get(legacy_code.strip().upper())


def to_legacy_reason(modern_code: str) -> str | None:
    """``BENEFICIARY_NAME_MISMATCH`` -> ``R03``; ``None`` when there is no legacy code.

    ``FX_QUOTE_EXPIRED`` and any other reason introduced after the desk was
    retired has no legacy equivalent and returns ``None``.
    """
    return MODERN_REASON_MAP.get(modern_code.strip().upper())


def normalize_reason_code(reason_code: str) -> str | None:
    """Return the legacy ``Rnn`` code for a legacy or modern spelling, else ``None``."""
    key = reason_code.strip().upper()
    if key in LEGACY_REASON_SEVERITY:
        return key
    return MODERN_REASON_MAP.get(key)


def normalize_segment(segment: str) -> str:
    """Return the desk's segment byte: ``I``/``C``/``R`` or ``"?"`` for anything else.

    The VB6 never rejected a segment; an unrecognized value simply fell into
    the ``Case Else`` branch and was routed to ``CORP-STD``. ``"?"`` is
    returned so callers can see that happened.
    """
    return _SEGMENT_ALIASES.get(segment.strip().upper(), "?")


def _require_decimal(value: object) -> Decimal:
    """Reject anything that is not a ``Decimal`` - in particular ``float`` (see docs: money)."""
    if not isinstance(value, Decimal):
        raise TypeError(
            f"amount_usd must be a decimal.Decimal, got {type(value).__name__}; "
            "floats are never accepted for money"
        )
    return value


# --------------------------------------------------------------------------- #
# RouteException
# --------------------------------------------------------------------------- #


def route_exception(reason_code: str, amount_usd: Decimal, segment: str) -> RoutingResult:
    """Route a held payment's exception exactly as ``RouteException`` did.

    :param reason_code: legacy ``Rnn`` code or modern ``reason_code``; unknown
        codes are routed with medium severity and ``legacy_reason_code=None``.
    :param amount_usd: payment value in USD (``Decimal``; floats are refused).
        The VB6 parameter was ``Currency`` (fixed-point, four decimals).
    :param segment: ``I``/``C``/``R`` or a ``CustomerSegment`` name.
    """
    amount = _require_decimal(amount_usd)

    legacy_code = normalize_reason_code(reason_code)
    segment_code = normalize_segment(segment)

    # SeverityForReason: table lookup, Case Else -> SEV_MEDIUM
    severity = (
        LEGACY_REASON_SEVERITY[legacy_code]
        if legacy_code is not None
        else DEFAULT_SEVERITY_UNKNOWN_REASON
    )

    # Select Case True ... queue selection, screening evaluated first
    if legacy_code == REASON_SCREENING:
        queue = QUEUE_FCR_SCREEN
        severity = SEVERITY_CRITICAL
        requires_supervisor = True
    else:
        if segment_code == "I" and amount >= HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD:
            queue = QUEUE_INST_HV
        elif segment_code == "R":
            queue = QUEUE_RETAIL_STD
        else:
            queue = QUEUE_CORP_STD
        requires_supervisor = (
            severity >= SUPERVISOR_SEVERITY_THRESHOLD or amount >= SUPERVISOR_AMOUNT_THRESHOLD_USD
        )

    return RoutingResult(
        queue=queue,
        severity=severity,
        requires_supervisor=requires_supervisor,
        legacy_reason_code=legacy_code,
    )
