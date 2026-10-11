"""Golden-master parity for the VB6 ``modExceptionRouting`` routing rules.

Visual Basic 6 cannot be compiled or executed on the build machines, so parity
is established two ways:

1. the Python reference must reproduce every fixture in
   ``fixtures/exception_routing_cases.json`` for both the legacy and the
   modern spelling of the reason code;
2. the constant tables in ``legacy/vb6/modExceptionRouting.bas`` (queue codes,
   thresholds, severity per reason, reason text) are parsed from the source
   and compared with the Python module, so the two cannot drift silently.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

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
    SUPERVISOR_AMOUNT_THRESHOLD_USD,
    SUPERVISOR_SEVERITY_THRESHOLD,
    route_exception,
    to_legacy_reason,
    to_modern_reason,
)

pytestmark = pytest.mark.legacy

REFERENCE_TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = REFERENCE_TESTS_DIR / "fixtures"
VB6_MODULE = REFERENCE_TESTS_DIR.parents[1] / "legacy" / "vb6" / "modExceptionRouting.bas"


def _load_cases(name: str) -> list[dict[str, Any]]:
    document = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = document["cases"]
    return cases


ROUTING_CASES = _load_cases("exception_routing_cases.json")


def _case_id(case: dict[str, Any]) -> str:
    reason = case["reason_code"].strip()
    segment = case["segment"].strip()
    return f"{case['id']}-{reason}-{case['amount_usd']}-{segment}"


# --------------------------------------------------------------------------- #
# 1. Python reference vs fixtures
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case", ROUTING_CASES, ids=_case_id)
def test_python_reference_matches_fixture_with_legacy_code(case: dict[str, Any]) -> None:
    result = route_exception(case["reason_code"], Decimal(case["amount_usd"]), case["segment"])
    assert result.queue == case["expected_queue"], case["note"]
    assert result.severity == case["expected_severity"], case["note"]
    assert result.requires_supervisor is case["expected_requires_supervisor"], case["note"]
    assert result.legacy_reason_code == case["expected_legacy_reason_code"], case["note"]


@pytest.mark.parametrize(
    "case",
    [case for case in ROUTING_CASES if case["modern_reason_code"]],
    ids=_case_id,
)
def test_python_reference_matches_fixture_with_modern_code(case: dict[str, Any]) -> None:
    legacy = route_exception(case["reason_code"], Decimal(case["amount_usd"]), case["segment"])
    modern = route_exception(
        case["modern_reason_code"], Decimal(case["amount_usd"]), case["segment"]
    )
    assert modern == legacy


def test_fixture_file_has_minimum_size_and_coverage() -> None:
    assert len(ROUTING_CASES) >= 20
    ids = [case["id"] for case in ROUTING_CASES]
    assert len(ids) == len(set(ids))
    codes = {case["expected_legacy_reason_code"] for case in ROUTING_CASES} - {None}
    assert codes == set(LEGACY_REASON_MAP), "every legacy reason code needs at least one case"
    assert {case["expected_queue"] for case in ROUTING_CASES} == {
        QUEUE_RETAIL_STD,
        QUEUE_CORP_STD,
        QUEUE_INST_HV,
        QUEUE_FCR_SCREEN,
    }
    assert {case["expected_severity"] for case in ROUTING_CASES} == {1, 2, 3, 4}
    assert any(case["expected_legacy_reason_code"] is None for case in ROUTING_CASES)
    hero = [
        case
        for case in ROUTING_CASES
        if case["reason_code"].strip() == "R03"
        and case["amount_usd"] == "480000.00"
        and case["segment"].strip().upper() == "I"
    ]
    assert hero and hero[0]["expected_queue"] == QUEUE_INST_HV
    for case in ROUTING_CASES:
        modern = case["modern_reason_code"]
        legacy = case["expected_legacy_reason_code"]
        assert (modern is None) == (legacy is None)
        if modern is not None:
            assert LEGACY_REASON_MAP[legacy] == modern


def test_reason_maps_are_inverse_and_complete() -> None:
    assert set(LEGACY_REASON_MAP) == {f"R{n:02d}" for n in range(1, 12)}
    assert set(LEGACY_REASON_SEVERITY) == set(LEGACY_REASON_MAP)
    assert set(LEGACY_REASON_TITLES) == set(LEGACY_REASON_MAP)
    assert {to_legacy_reason(m) for m in LEGACY_REASON_MAP.values()} == set(LEGACY_REASON_MAP)
    assert {to_modern_reason(code) for code in LEGACY_REASON_MAP} == set(MODERN_REASON_MAP)
    assert to_legacy_reason("FX_QUOTE_EXPIRED") is None
    assert to_modern_reason("R12") is None


# --------------------------------------------------------------------------- #
# 2. Static parity with the VB6 source
# --------------------------------------------------------------------------- #

_CONST_RE = re.compile(
    r"^\s*Public\s+Const\s+(?P<name>\w+)\s+As\s+(?P<type>String|Integer|Currency)"
    r"\s*=\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)
_SEVERITY_CASE_RE = re.compile(
    r"^\s*Case\s+(?P<reason>REASON_\w+):\s*SeverityForReason\s*=\s*(?P<sev>SEV_\w+)\s*$",
    re.MULTILINE,
)
_TEXT_CASE_RE = re.compile(
    r'^\s*Case\s+(?P<reason>REASON_\w+):\s*ReasonText\s*=\s*"(?P<text>[^"]+)"\s*$',
    re.MULTILINE,
)
_ELSE_SEVERITY_RE = re.compile(
    r"^\s*Case Else:\s*SeverityForReason\s*=\s*(?P<sev>SEV_\w+)", re.MULTILINE
)


def _vb6_constants(source: str) -> dict[str, str | int | Decimal]:
    constants: dict[str, str | int | Decimal] = {}
    for match in _CONST_RE.finditer(source):
        raw = match.group("value")
        kind = match.group("type")
        if kind == "String":
            constants[match.group("name")] = raw.strip('"')
        elif kind == "Integer":
            constants[match.group("name")] = int(raw)
        else:
            constants[match.group("name")] = Decimal(raw.rstrip("@"))
    return constants


@pytest.fixture(scope="module")
def vb6_source() -> str:
    return VB6_MODULE.read_text(encoding="utf-8")


def test_vb6_module_declares_expected_structure(vb6_source: str) -> None:
    assert vb6_source.startswith('Attribute VB_Name = "modExceptionRouting"')
    assert "Option Explicit" in vb6_source
    assert "Public Type RoutingResult" in vb6_source
    assert re.search(
        r"Public Function RouteException\(ByVal reasonCode As String,\s*_\s*"
        r"ByVal amountUsd As Currency,\s*_\s*ByVal segment As String\) As RoutingResult",
        vb6_source,
    )


def test_vb6_constants_match_python_reference(vb6_source: str) -> None:
    constants = _vb6_constants(vb6_source)
    assert constants["QUEUE_RETAIL_STD"] == QUEUE_RETAIL_STD
    assert constants["QUEUE_CORP_STD"] == QUEUE_CORP_STD
    assert constants["QUEUE_INST_HV"] == QUEUE_INST_HV
    assert constants["QUEUE_FCR_SCREEN"] == QUEUE_FCR_SCREEN
    assert constants["HV_AMOUNT_THRESHOLD"] == HIGH_VALUE_INSTITUTIONAL_THRESHOLD_USD
    assert constants["SUPERVISOR_AMOUNT_THRESHOLD"] == SUPERVISOR_AMOUNT_THRESHOLD_USD
    assert constants["SUPERVISOR_SEVERITY_THRESHOLD"] == SUPERVISOR_SEVERITY_THRESHOLD
    assert constants["SEV_LOW"] == 1
    assert constants["SEV_MEDIUM"] == 2
    assert constants["SEV_HIGH"] == 3
    assert constants["SEV_CRITICAL"] == 4
    reason_constants = {
        name: value for name, value in constants.items() if name.startswith("REASON_")
    }
    assert set(reason_constants.values()) == set(LEGACY_REASON_MAP)


def test_vb6_severity_table_matches_python_reference(vb6_source: str) -> None:
    constants = _vb6_constants(vb6_source)
    table = {
        str(constants[m.group("reason")]): int(constants[m.group("sev")])
        for m in _SEVERITY_CASE_RE.finditer(vb6_source)
    }
    assert table == dict(LEGACY_REASON_SEVERITY)
    else_match = _ELSE_SEVERITY_RE.search(vb6_source)
    assert else_match is not None
    assert constants[else_match.group("sev")] == DEFAULT_SEVERITY_UNKNOWN_REASON


def test_vb6_reason_text_table_matches_python_reference(vb6_source: str) -> None:
    constants = _vb6_constants(vb6_source)
    table = {
        str(constants[m.group("reason")]): m.group("text")
        for m in _TEXT_CASE_RE.finditer(vb6_source)
    }
    assert table == dict(LEGACY_REASON_TITLES)
