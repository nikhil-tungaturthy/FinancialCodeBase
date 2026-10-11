"""Unit tests for the modExceptionRouting Python reference."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.integrations.legacy.exception_routing import (
    DEFAULT_SEVERITY_UNKNOWN_REASON,
    HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD,
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
    SUPERVISOR_AMOUNT_THRESHOLD_USD,
    RoutingResult,
    normalize_reason_code,
    normalize_segment,
    route_exception,
    to_legacy_reason,
    to_modern_reason,
)

D = Decimal


def test_hero_exception_mgb_exc_0231() -> None:
    result = route_exception("BENEFICIARY_NAME_MISMATCH", D("480000.00"), "INSTITUTIONAL")
    assert result == RoutingResult(
        queue=QUEUE_INST_HV, severity=3, requires_supervisor=True, legacy_reason_code="R03"
    )
    assert result.severity_label == "HIGH"
    assert result.modern_reason_code == "BENEFICIARY_NAME_MISMATCH"


# --------------------------------------------------------------------------- #
# Queue selection
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("segment", ["I", "C", "R", "X", ""])
@pytest.mark.parametrize("amount", ["0.00", "99999.99", "250000.00", "5000000.00"])
def test_screening_always_routes_to_fcr_screen(segment: str, amount: str) -> None:
    result = route_exception("R07", D(amount), segment)
    assert result.queue == QUEUE_FCR_SCREEN
    assert result.severity == 4
    assert result.requires_supervisor is True
    assert result.legacy_reason_code == "R07"


def test_institutional_high_value_threshold_is_inclusive() -> None:
    below = route_exception("R03", HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD - D("0.01"), "I")
    at = route_exception("R03", HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD, "I")
    assert below.queue == QUEUE_CORP_STD
    assert at.queue == QUEUE_INST_HV


def test_only_institutional_reaches_inst_hv() -> None:
    for segment in ("C", "R", "X", "INTERNAL"):
        assert route_exception("R05", D("10000000.00"), segment).queue != QUEUE_INST_HV


@pytest.mark.parametrize(
    ("segment", "expected"),
    [
        ("R", QUEUE_RETAIL_STD),
        ("retail", QUEUE_RETAIL_STD),
        ("C", QUEUE_CORP_STD),
        ("CORPORATE", QUEUE_CORP_STD),
        ("I", QUEUE_CORP_STD),  # below the HV threshold
        ("INTERNAL", QUEUE_CORP_STD),
        ("", QUEUE_CORP_STD),
        ("?", QUEUE_CORP_STD),
    ],
)
def test_standard_queue_by_segment(segment: str, expected: str) -> None:
    assert route_exception("R06", D("20000.00"), segment).queue == expected


def test_segment_normalization() -> None:
    assert normalize_segment(" i ") == "I"
    assert normalize_segment("Corporate") == "C"
    assert normalize_segment("RETAIL") == "R"
    assert normalize_segment("INTERNAL") == "C"
    assert normalize_segment("Z") == "?"


# --------------------------------------------------------------------------- #
# Severity and supervisor rules
# --------------------------------------------------------------------------- #


def test_severity_table_matches_policy_defaults() -> None:
    assert dict(LEGACY_REASON_SEVERITY) == {
        "R01": 3,
        "R02": 2,
        "R03": 3,
        "R04": 3,
        "R05": 3,
        "R06": 2,
        "R07": 4,
        "R08": 2,
        "R09": 1,
        "R10": 2,
        "R11": 3,
    }


@pytest.mark.parametrize("code", sorted(LEGACY_REASON_MAP))
def test_supervisor_required_when_severity_at_least_three(code: str) -> None:
    result = route_exception(code, D("1.00"), "C")
    expected = LEGACY_REASON_SEVERITY[code] >= 3 or code == "R07"
    assert result.requires_supervisor is expected


def test_supervisor_amount_threshold_is_inclusive() -> None:
    low_severity = "R09"
    assert (
        route_exception(
            low_severity, SUPERVISOR_AMOUNT_THRESHOLD_USD - D("0.01"), "R"
        ).requires_supervisor
        is False
    )
    assert (
        route_exception(low_severity, SUPERVISOR_AMOUNT_THRESHOLD_USD, "R").requires_supervisor
        is True
    )


def test_unknown_reason_code_gets_medium_severity_and_no_legacy_code() -> None:
    result = route_exception("FX_QUOTE_EXPIRED", D("12000.00"), "C")
    assert result == RoutingResult(
        queue=QUEUE_CORP_STD,
        severity=DEFAULT_SEVERITY_UNKNOWN_REASON,
        requires_supervisor=False,
        legacy_reason_code=None,
    )
    assert result.modern_reason_code is None
    assert route_exception("R99", D("150000.00"), "R").requires_supervisor is True


def test_inputs_are_trimmed_and_upper_cased() -> None:
    assert route_exception(" r03 ", D("480000.00"), " i ") == route_exception(
        "R03", D("480000.00"), "I"
    )
    assert route_exception("beneficiary_name_mismatch", D("1.00"), "c").legacy_reason_code == "R03"


@pytest.mark.parametrize("bad", [480000.0, 480000, "480000"])
def test_non_decimal_amounts_are_rejected(bad: object) -> None:
    with pytest.raises(TypeError):
        route_exception("R03", bad, "I")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Code mapping
# --------------------------------------------------------------------------- #


def test_legacy_reason_map_matches_spec() -> None:
    assert dict(LEGACY_REASON_MAP) == {
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
    assert dict(MODERN_REASON_MAP) == {v: k for k, v in LEGACY_REASON_MAP.items()}
    assert set(LEGACY_REASON_TITLES) == set(LEGACY_REASON_MAP)


def test_round_trip_helpers() -> None:
    for legacy, modern in LEGACY_REASON_MAP.items():
        assert to_modern_reason(legacy) == modern
        assert to_legacy_reason(modern) == legacy
        assert normalize_reason_code(legacy) == legacy
        assert normalize_reason_code(modern) == legacy
    assert to_modern_reason("r03") == "BENEFICIARY_NAME_MISMATCH"
    assert to_legacy_reason(" screening_review ") == "R07"
    assert to_legacy_reason("FX_QUOTE_EXPIRED") is None
    assert to_modern_reason("R00") is None
    assert normalize_reason_code("nonsense") is None


def test_constants_are_immutable_and_complete() -> None:
    assert {QUEUE_RETAIL_STD, QUEUE_CORP_STD, QUEUE_INST_HV, QUEUE_FCR_SCREEN} == QUEUES
    assert dict(SEVERITY_LABELS) == {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
    with pytest.raises(TypeError):
        LEGACY_REASON_MAP["R12"] = "X"  # type: ignore[index]
