"""Golden-master parity for the FEECALC01 fee tariff.

Three layers, all marked ``legacy``:

1. the Python reference (:mod:`app.integrations.legacy.feecalc`) must reproduce
   every fixture in ``fixtures/feecalc_cases.json``;
2. the fixture file itself must cover the band edges, the cap, every segment,
   the SWIFT surcharge and the hero payment, so nobody can quietly thin it out;
3. when GnuCOBOL is installed the real COBOL program is compiled and executed
   on the fixture input and on a deterministic pseudo-random sweep, and its
   FEEOUT must agree record-for-record with the fixtures and with Python.
   Without ``cobc`` those tests skip with the message from the build spec.

The COBOL fixtures (``cobc``, ``feecalc01_binary``, ``feecalc01_runner``) live
in ``conftest.py``; the runner returns ``(return_code, console, feeout_lines)``.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.integrations.legacy.feecalc import (
    FEE_BANDS,
    FEE_CAP,
    FeeCalcInputError,
    calculate_wire_fee,
    encode_feein_record,
    parse_feeout_record,
)

pytestmark = pytest.mark.legacy

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FeeCalcRunner = Callable[[Sequence[str]], tuple[int, str, list[str]]]
HERO = {"amount": "480000.00", "segment": "I", "rail": "WIRE", "expected_fee": "47.20"}


def _load_cases(name: str) -> list[dict[str, Any]]:
    document = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = document["cases"]
    return cases


FEE_CASES = _load_cases("feecalc_cases.json")


def _case_id(case: dict[str, Any]) -> str:
    return f"{case['id']}-{case['amount']}-{case['segment']}-{case['rail']}"


# --------------------------------------------------------------------------- #
# 1. Python reference vs fixtures
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("case", FEE_CASES, ids=_case_id)
def test_python_reference_matches_fixture(case: dict[str, Any]) -> None:
    result = calculate_wire_fee(Decimal(case["amount"]), case["segment"], case["rail"])
    assert result.fee == Decimal(case["expected_fee"]), case["note"]
    assert result.band == case["expected_band"], case["note"]
    assert result.capped is case["expected_capped"], case["note"]


def test_python_reference_prices_hero_payment() -> None:
    result = calculate_wire_fee(Decimal(HERO["amount"]), HERO["segment"], HERO["rail"])
    assert result.fee == Decimal("47.20")
    assert result.band == 3
    assert result.base_fee == Decimal("35.00")
    assert result.bps_component == Decimal("24.00")
    assert result.multiplier == Decimal("0.80")
    assert result.surcharge == Decimal("0.00")
    assert result.capped is False


# --------------------------------------------------------------------------- #
# 2. Fixture coverage guarantees
# --------------------------------------------------------------------------- #


def test_fixture_file_has_minimum_size_and_unique_ids() -> None:
    assert len(FEE_CASES) >= 24
    ids = [case["id"] for case in FEE_CASES]
    assert len(ids) == len(set(ids))
    for case in FEE_CASES:
        assert set(case) >= {"amount", "segment", "rail", "expected_fee", "note"}
        assert Decimal(case["expected_fee"]).as_tuple().exponent == -2


def test_fixture_file_covers_every_band_edge() -> None:
    amounts = {case["amount"] for case in FEE_CASES}
    required = {
        "10000.00",
        "10000.01",
        "100000.00",
        "100000.01",
        "1000000.00",
        "1000000.01",
    }
    assert required <= amounts, sorted(required - amounts)
    bands = {case["expected_band"] for case in FEE_CASES}
    assert bands == {band.number for band in FEE_BANDS}


def test_fixture_file_covers_segments_rails_cap_and_hero() -> None:
    assert {case["segment"] for case in FEE_CASES} == {"I", "C", "R"}
    assert {case["rail"] for case in FEE_CASES} == {"WIRE", "SWIFT"}
    assert any(case["expected_capped"] for case in FEE_CASES)
    assert any(case["expected_capped"] and case["rail"] == "SWIFT" for case in FEE_CASES), (
        "need a case proving the surcharge is added after the cap"
    )
    hero_matches = [
        case
        for case in FEE_CASES
        if (case["amount"], case["segment"], case["rail"])
        == (HERO["amount"], HERO["segment"], HERO["rail"])
    ]
    assert hero_matches, "hero case 480000.00/I/WIRE missing from fixtures"
    assert hero_matches[0]["expected_fee"] == HERO["expected_fee"]


# --------------------------------------------------------------------------- #
# 3. Compiled COBOL vs fixtures and vs Python
# --------------------------------------------------------------------------- #


def test_cobol_binary_matches_fixtures(
    feecalc01_runner: FeeCalcRunner, feecalc_cases: list[dict[str, Any]]
) -> None:
    feein = [
        encode_feein_record(Decimal(case["amount"]), case["segment"], case["rail"])
        for case in feecalc_cases
    ]
    return_code, console, feeout_lines = feecalc01_runner(feein)
    assert return_code == 0, f"FEECALC01 RC={return_code}\n{console}"
    assert len(feeout_lines) == len(feecalc_cases)
    assert "FEECALC01: END" in console

    mismatches: list[str] = []
    for case, line in zip(feecalc_cases, feeout_lines, strict=True):
        record = parse_feeout_record(line)
        expected_fee = Decimal(case["expected_fee"])
        if (
            record.status_code != "00"
            or record.fee != expected_fee
            or record.band != case["expected_band"]
            or record.capped is not case["expected_capped"]
        ):
            mismatches.append(
                f"{case['id']} {case['amount']} {case['segment']} {case['rail']}: "
                f"COBOL fee={record.fee} band={record.band} cap={record.capped} "
                f"status={record.status_code}; expected fee={expected_fee} "
                f"band={case['expected_band']} cap={case['expected_capped']}"
            )
        # The echo must be byte-identical to what we sent.
        assert line[:21] == encode_feein_record(
            Decimal(case["amount"]), case["segment"], case["rail"]
        )
    assert not mismatches, "\n".join(mismatches)


def test_cobol_rejects_malformed_records_with_status_codes(
    feecalc01_runner: FeeCalcRunner,
) -> None:
    good = encode_feein_record(Decimal("480000.00"), "I", "WIRE")
    feein = [
        good,
        "000000048000000XWIRE ",  # unknown segment       -> 01
        "000000048000000IACH  ",  # unpriced rail         -> 02
        "00000004800000AIWIRE ",  # non-numeric amount    -> 03
        "",  # blank line is skipped, no output
        "000000048000000IWIRE_",  # underscore alias of 'WIRE '
    ]
    return_code, console, feeout_lines = feecalc01_runner(feein)
    assert return_code == 4, console
    records = [parse_feeout_record(line) for line in feeout_lines]
    assert [record.status_code for record in records] == ["00", "01", "02", "03", "00"]
    assert records[0].fee == Decimal("47.20")
    assert records[-1].fee == Decimal("47.20")
    for rejected in records[1:4]:
        assert rejected.fee == Decimal("0.00")
        assert rejected.band == 0
        assert rejected.capped is False
    assert "ERRORS=0000003" in console
    assert "SKIPPED=0000001" in console

    # The Python reference refuses the same inputs with the same status codes.
    with pytest.raises(FeeCalcInputError) as bad_segment:
        calculate_wire_fee(Decimal("480000.00"), "X", "WIRE")
    assert bad_segment.value.status_code == "01"
    with pytest.raises(FeeCalcInputError) as bad_rail:
        calculate_wire_fee(Decimal("480000.00"), "I", "ACH")
    assert bad_rail.value.status_code == "02"


def _deterministic_amounts(count: int) -> list[Decimal]:
    """Amounts spread over every band and dense around edges and ties, seeded."""
    rng = random.Random(20260318)
    amounts: set[Decimal] = set()
    bounds = [band.upper_bound for band in FEE_BANDS[:-1]] + [Decimal("8000200.00")]
    for bound in bounds:
        for offset_cents in range(-3, 4):
            candidate = bound + Decimal(offset_cents).scaleb(-2)
            if candidate >= 0:
                amounts.add(candidate)
    ranges = [
        (0, 10_000_00),
        (10_000_01, 100_000_00),
        (100_000_01, 1_000_000_00),
        (1_000_000_01, 12_000_000_00),
    ]
    while len(amounts) < count:
        low, high = rng.choice(ranges)
        amounts.add(Decimal(rng.randint(low, high)).scaleb(-2))
    return sorted(amounts)


def test_cobol_and_python_agree_on_seeded_sweep(feecalc01_runner: FeeCalcRunner) -> None:
    amounts = _deterministic_amounts(240)
    combos = [
        (amount, segment, rail)
        for amount in amounts
        for segment in "ICR"
        for rail in ("WIRE", "SWIFT")
    ]
    return_code, console, feeout_lines = feecalc01_runner(
        [encode_feein_record(a, s, r) for a, s, r in combos]
    )
    assert return_code == 0, console
    assert len(feeout_lines) == len(combos)
    disagreements: list[str] = []
    for (amount, segment, rail), line in zip(combos, feeout_lines, strict=True):
        cobol = parse_feeout_record(line)
        python = calculate_wire_fee(amount, segment, rail)
        if (cobol.fee, cobol.band, cobol.capped) != (python.fee, python.band, python.capped):
            disagreements.append(
                f"{amount} {segment} {rail}: COBOL {cobol.fee}/{cobol.band}/{cobol.capped} "
                f"vs Python {python.fee}/{python.band}/{python.capped}"
            )
    assert not disagreements, "\n".join(disagreements[:20])
    # Sanity: the sweep really exercised the cap and every band, and no fee
    # can exceed the capped retail SWIFT maximum.
    records = [parse_feeout_record(line) for line in feeout_lines]
    assert any(record.capped for record in records)
    assert {record.band for record in records} == {1, 2, 3, 4}
    highest_possible = FEE_CAP * Decimal("1.10") + Decimal("12.00")
    assert all(record.fee <= highest_possible for record in records)
