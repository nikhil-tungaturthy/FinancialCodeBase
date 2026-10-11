"""Unit tests for the FEECALC01 Python reference (no COBOL toolchain needed)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.integrations.legacy.feecalc import (
    FEE_BANDS,
    FEE_CAP,
    FEEIN_RECORD_LENGTH,
    FEEOUT_RECORD_LENGTH,
    MAX_AMOUNT,
    SEGMENT_MULTIPLIERS,
    SWIFT_SURCHARGE,
    FeeCalcInputError,
    FeeCalcResult,
    calculate_wire_fee,
    encode_feein_record,
    legacy_segment_code,
    normalize_rail_code,
    normalize_segment_code,
    parse_feeout_record,
    select_band,
)

D = Decimal


def fee(amount: str, segment: str = "C", rail: str = "WIRE") -> Decimal:
    return calculate_wire_fee(D(amount), segment, rail).fee


# --------------------------------------------------------------------------- #
# Hero and band selection
# --------------------------------------------------------------------------- #


def test_hero_payment_mgb_pay_1042() -> None:
    result = calculate_wire_fee(D("480000.00"), "I", "WIRE")
    assert result == FeeCalcResult(
        fee=D("47.20"),
        band=3,
        base_fee=D("35.00"),
        bps_component=D("24.00"),
        multiplier=D("0.80"),
        surcharge=D("0.00"),
        capped=False,
        banded_fee=D("59.00"),
        segment_code="I",
        rail_code="WIRE",
    )
    assert result.capped_fee == D("59.00")


@pytest.mark.parametrize(
    ("amount", "band"),
    [
        ("0.00", 1),
        ("9999.99", 1),
        ("10000.00", 1),
        ("10000.01", 2),
        ("100000.00", 2),
        ("100000.01", 3),
        ("1000000.00", 3),
        ("1000000.01", 4),
        ("9999999999999.99", 4),
    ],
)
def test_band_edges_are_inclusive_upper_bounds(amount: str, band: int) -> None:
    assert select_band(D(amount)).number == band
    assert calculate_wire_fee(D(amount), "C", "WIRE").band == band


def test_band_table_is_ascending_and_ends_at_field_maximum() -> None:
    bounds = [band.upper_bound for band in FEE_BANDS]
    assert bounds == sorted(bounds)
    assert bounds[-1] == MAX_AMOUNT
    assert [band.number for band in FEE_BANDS] == [1, 2, 3, 4]
    assert [band.base_fee for band in FEE_BANDS] == [D("15.00"), D("25.00"), D("35.00"), D("50.00")]
    assert [band.bps_rate for band in FEE_BANDS] == [
        D("0.000000"),
        D("0.000100"),
        D("0.000050"),
        D("0.000025"),
    ]


def test_fee_drops_when_crossing_into_band_four() -> None:
    # 35 + 50.00 = 85.00 in band 3 versus 50 + 25.00 = 75.00 in band 4.
    assert fee("1000000.00") == D("85.00")
    assert fee("1000000.01") == D("75.00")


# --------------------------------------------------------------------------- #
# Rounding
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("amount", "segment", "expected"),
    [
        ("10050.00", "C", "26.01"),  # 1.005 -> 1.01 (bankers' rounding would give 26.00)
        ("100100.00", "C", "40.01"),  # 5.005 -> 5.01
        ("1000200.00", "C", "75.01"),  # 25.005 -> 25.01
        ("11500.00", "R", "28.77"),  # 26.15 x 1.10 = 28.765 -> 28.77 (bankers' 28.76)
        ("10000.01", "C", "26.00"),  # 1.000001 -> 1.00
        ("123456.78", "I", "32.94"),  # 6.172839 -> 6.17; 41.17 x 0.80 = 32.936 -> 32.94
    ],
)
def test_round_half_up_at_both_rounding_points(amount: str, segment: str, expected: str) -> None:
    assert fee(amount, segment) == D(expected)


def test_bps_component_is_rounded_before_adding_base_fee() -> None:
    result = calculate_wire_fee(D("10050.00"), "C", "WIRE")
    assert result.bps_component == D("1.01")
    assert result.banded_fee == result.base_fee + result.bps_component


def test_results_are_always_two_decimal_places() -> None:
    for amount in ("0.01", "33333.33", "777777.77", "1234567.89", MAX_AMOUNT):
        for segment in SEGMENT_MULTIPLIERS:
            for rail in ("WIRE", "SWIFT"):
                result = calculate_wire_fee(D(amount), segment, rail)
                assert result.fee.as_tuple().exponent == -2
                assert result.bps_component.as_tuple().exponent == -2


def test_fee_formula_reconstructs_from_breakdown() -> None:
    for amount in ("5000.00", "48000.00", "480000.00", "4800000.00", "48000000.00"):
        for segment in SEGMENT_MULTIPLIERS:
            for rail in ("WIRE", "SWIFT"):
                r = calculate_wire_fee(D(amount), segment, rail)
                segment_fee = (r.capped_fee * r.multiplier).quantize(D("0.01"), ROUND_HALF_UP)
                assert r.fee == segment_fee + r.surcharge


# --------------------------------------------------------------------------- #
# Cap, multiplier, surcharge ordering
# --------------------------------------------------------------------------- #


def test_cap_is_strict_greater_than() -> None:
    at_cap = calculate_wire_fee(D("8000000.00"), "C", "WIRE")
    assert at_cap.banded_fee == FEE_CAP
    assert at_cap.capped is False
    assert at_cap.fee == D("250.00")

    just_below = calculate_wire_fee(D("8000199.99"), "C", "WIRE")
    assert just_below.capped is False
    assert just_below.fee == D("250.00")

    first_hit = calculate_wire_fee(D("8000200.00"), "C", "WIRE")
    assert first_hit.banded_fee == D("250.01")
    assert first_hit.capped is True
    assert first_hit.fee == D("250.00")


def test_cap_applies_before_multiplier_and_surcharge() -> None:
    retail = calculate_wire_fee(D("10000000.00"), "R", "WIRE")
    assert retail.capped is True
    assert retail.fee == D("275.00")  # 250.00 x 1.10, i.e. above the cap
    institutional_swift = calculate_wire_fee(D("10000000.00"), "I", "SWIFT")
    assert institutional_swift.fee == D("212.00")  # 250.00 x 0.80 + 12.00
    corporate_swift = calculate_wire_fee(D("25000000.00"), "C", "SWIFT")
    assert corporate_swift.fee == FEE_CAP + SWIFT_SURCHARGE


def test_maximum_amount_prices_without_overflow() -> None:
    result = calculate_wire_fee(MAX_AMOUNT, "R", "SWIFT")
    assert result.band == 4
    assert result.bps_component == D("250000000.00")  # 249,999,999.99999975 rounded
    assert result.capped is True
    assert result.fee == D("287.00")


@pytest.mark.parametrize(("segment", "expected"), [("I", "47.20"), ("C", "59.00"), ("R", "64.90")])
def test_segment_multipliers(segment: str, expected: str) -> None:
    assert fee("480000.00", segment) == D(expected)


@pytest.mark.parametrize(("segment", "expected"), [("I", "59.20"), ("C", "71.00"), ("R", "76.90")])
def test_swift_surcharge_added_after_multiplier(segment: str, expected: str) -> None:
    result = calculate_wire_fee(D("480000.00"), segment, "SWIFT")
    assert result.surcharge == SWIFT_SURCHARGE
    assert result.fee == D(expected)
    assert result.fee == fee("480000.00", segment, "WIRE") + SWIFT_SURCHARGE


# --------------------------------------------------------------------------- #
# Input normalization and validation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("I", "I"),
        ("c", "C"),
        (" r ", "R"),
        ("INSTITUTIONAL", "I"),
        ("Corporate", "C"),
        ("retail", "R"),
        ("INTERNAL", "C"),
    ],
)
def test_segment_normalization(value: str, expected: str) -> None:
    assert normalize_segment_code(value) == expected
    assert legacy_segment_code(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("WIRE", "WIRE"),
        ("WIRE ", "WIRE"),
        ("WIRE_", "WIRE"),
        ("wire_usd", "WIRE"),
        ("SWIFT", "SWIFT"),
        ("SWIFT_INTL", "SWIFT"),
    ],
)
def test_rail_normalization(value: str, expected: str) -> None:
    assert normalize_rail_code(value) == expected


def test_modern_enum_values_price_identically_to_legacy_codes() -> None:
    assert calculate_wire_fee(D("480000.00"), "INSTITUTIONAL", "WIRE_USD") == calculate_wire_fee(
        D("480000.00"), "I", "WIRE"
    )
    assert calculate_wire_fee(D("480000"), "I", "WIRE").fee == D("47.20")


@pytest.mark.parametrize("segment", ["X", "", "N", "INST", "RETAIL CUSTOMER"])
def test_unknown_segment_is_status_01(segment: str) -> None:
    with pytest.raises(FeeCalcInputError) as info:
        calculate_wire_fee(D("1.00"), segment, "WIRE")
    assert info.value.status_code == "01"


@pytest.mark.parametrize("rail", ["ACH", "ACH_USD", "SEPA_EUR", "CHAPS_GBP", "INTERNAL_BOOK", ""])
def test_unpriced_rail_is_status_02(rail: str) -> None:
    with pytest.raises(FeeCalcInputError) as info:
        calculate_wire_fee(D("1.00"), "C", rail)
    assert info.value.status_code == "02"


@pytest.mark.parametrize(
    "amount",
    [D("-0.01"), D("0.001"), D("480000.005"), MAX_AMOUNT + D("0.01"), D("NaN"), D("Infinity")],
)
def test_amount_outside_pic_9_13_v99_is_status_03(amount: Decimal) -> None:
    with pytest.raises(FeeCalcInputError) as info:
        calculate_wire_fee(amount, "C", "WIRE")
    assert info.value.status_code == "03"


def test_validation_order_matches_cobol_amount_then_segment_then_rail() -> None:
    with pytest.raises(FeeCalcInputError) as info:
        calculate_wire_fee(D("-1"), "X", "ACH")
    assert info.value.status_code == "03"
    with pytest.raises(FeeCalcInputError) as info:
        calculate_wire_fee(D("1"), "X", "ACH")
    assert info.value.status_code == "01"


@pytest.mark.parametrize("bad", [480000.0, 480000, "480000.00", None])
def test_non_decimal_amounts_are_rejected(bad: object) -> None:
    with pytest.raises(TypeError):
        calculate_wire_fee(bad, "I", "WIRE")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Breakdown and record layouts
# --------------------------------------------------------------------------- #


def test_breakdown_serializes_money_as_strings() -> None:
    breakdown = calculate_wire_fee(D("480000.00"), "I", "SWIFT").as_breakdown()
    assert breakdown["program"] == "FEECALC01"
    assert breakdown["fee"] == "59.20"
    assert breakdown["base_fee"] == "35.00"
    assert breakdown["bps_component"] == "24.00"
    assert breakdown["multiplier"] == "0.80"
    assert breakdown["surcharge"] == "12.00"
    assert breakdown["capped"] == "false"
    assert all(isinstance(value, str) for value in breakdown.values())


def test_feein_record_layout() -> None:
    record = encode_feein_record(D("480000.00"), "INSTITUTIONAL", "WIRE_USD")
    assert record == "000000048000000IWIRE "
    assert len(record) == FEEIN_RECORD_LENGTH
    assert encode_feein_record(D("0.01"), "R", "SWIFT") == "000000000000001RSWIFT"
    assert encode_feein_record(MAX_AMOUNT, "C", "WIRE") == "999999999999999CWIRE "


def test_feeout_record_round_trip() -> None:
    line = "000000048000000IWIRE 0000047203N00"
    assert len(line) == FEEOUT_RECORD_LENGTH
    record = parse_feeout_record(line + "\n")
    assert record.amount == D("480000.00")
    assert record.segment_code == "I"
    assert record.rail_code == "WIRE"
    assert record.fee == D("47.20")
    assert record.band == 3
    assert record.capped is False
    assert record.status_code == "00"
    assert record.ok is True

    rejected = parse_feeout_record("000000048000000XWIRE 0000000000N01")
    assert rejected.ok is False
    assert rejected.status_code == "01"
    assert rejected.fee == D("0.00")

    capped = parse_feeout_record("999999999999999RSWIFT0000287004Y00")
    assert capped.capped is True
    assert capped.fee == D("287.00")


def test_feeout_parser_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="length"):
        parse_feeout_record("000000048000000IWIRE 00000472")
