"""Python reference implementations of the retired legacy components.

* :mod:`app.integrations.legacy.feecalc` - COBOL ``FEECALC01`` wire/SWIFT fee
  tariff (``legacy/cobol``). Used by ``domain/fees/service.py`` for the
  legacy-governed rails ``WIRE_USD`` and ``SWIFT_INTL``.
* :mod:`app.integrations.legacy.exception_routing` - VB6
  ``modExceptionRouting`` queue/severity routing (``legacy/vb6``). Used by
  ``domain/exceptions/classification.py``.

Both modules are pure, standard-library-only, and covered by golden-master
tests in ``legacy/reference-tests`` (see ``docs/architecture/legacy-modernization.md``).
"""

from app.integrations.legacy.exception_routing import (
    LEGACY_REASON_MAP,
    LEGACY_REASON_SEVERITY,
    LEGACY_REASON_TITLES,
    MODERN_REASON_MAP,
    QUEUE_CORP_STD,
    QUEUE_FCR_SCREEN,
    QUEUE_INST_HV,
    QUEUE_RETAIL_STD,
    QUEUES,
    SEVERITY_LABELS,
    RoutingResult,
    route_exception,
    to_legacy_reason,
    to_modern_reason,
)
from app.integrations.legacy.feecalc import (
    FEE_BANDS,
    FEE_CAP,
    FEESCHED_VERSION,
    SEGMENT_MULTIPLIERS,
    SWIFT_SURCHARGE,
    FeeBand,
    FeeCalcInputError,
    FeeCalcResult,
    calculate_wire_fee,
    legacy_segment_code,
    normalize_rail_code,
    normalize_segment_code,
)

__all__ = [
    "FEESCHED_VERSION",
    "FEE_BANDS",
    "FEE_CAP",
    "LEGACY_REASON_MAP",
    "LEGACY_REASON_SEVERITY",
    "LEGACY_REASON_TITLES",
    "MODERN_REASON_MAP",
    "QUEUES",
    "QUEUE_CORP_STD",
    "QUEUE_FCR_SCREEN",
    "QUEUE_INST_HV",
    "QUEUE_RETAIL_STD",
    "SEGMENT_MULTIPLIERS",
    "SEVERITY_LABELS",
    "SWIFT_SURCHARGE",
    "FeeBand",
    "FeeCalcInputError",
    "FeeCalcResult",
    "RoutingResult",
    "calculate_wire_fee",
    "legacy_segment_code",
    "normalize_rail_code",
    "normalize_segment_code",
    "route_exception",
    "to_legacy_reason",
    "to_modern_reason",
]
