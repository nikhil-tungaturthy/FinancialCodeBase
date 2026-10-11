"""Decimal rounding, currency quantisation, scenario FX and money string formatting."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.money.currency import (
    MINOR_UNITS,
    as_currency,
    format_amount,
    is_quantized,
    minor_units,
    minor_units_or_none,
    quantize,
)
from app.domain.money.fx import (
    SCENARIO_RATES_TO_USD,
    from_usd,
    rate_to_usd,
    reference_rates_as_strings,
    to_usd,
)
from app.domain.money.rounding import apply_basis_points, round_half_up, to_decimal
from app.models.enums import Currency
from app.schemas.common import format_money


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        ("2.345", 2, "2.35"),
        ("2.344", 2, "2.34"),
        ("2.5", 0, "3"),
        ("3.5", 0, "4"),
        ("-2.345", 2, "-2.35"),
        ("0.005", 2, "0.01"),
        ("59.0000", 2, "59.00"),
        ("47.195", 2, "47.20"),
    ],
)
def test_round_half_up(value: str, places: int, expected: str) -> None:
    assert round_half_up(Decimal(value), places) == Decimal(expected)


def test_round_half_up_rejects_floats_and_negative_places() -> None:
    with pytest.raises(TypeError):
        round_half_up(2.345, 2)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        round_half_up(Decimal("1"), -1)


def test_to_decimal_rejects_float_and_bool() -> None:
    assert to_decimal("480000.00") == Decimal("480000.00")
    assert to_decimal(5) == Decimal(5)
    with pytest.raises(TypeError):
        to_decimal(1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_decimal(True)  # type: ignore[arg-type]


def test_apply_basis_points_matches_fee_schedule_arithmetic() -> None:
    # 480,000 x 0.5 bps = 24.00 (the hero payment's variable fee component).
    assert apply_basis_points(Decimal("480000.00"), Decimal("0.5")) == Decimal("24.00")
    assert apply_basis_points(Decimal("10000.01"), 1) == Decimal("1.00")


def test_minor_units_table() -> None:
    assert MINOR_UNITS[Currency.JPY] == 0
    assert all(MINOR_UNITS[c] == 2 for c in Currency if c is not Currency.JPY)
    assert minor_units("usd") == 2
    assert minor_units_or_none("JPY") == 0
    assert minor_units_or_none("XXX") is None
    assert minor_units_or_none(None) is None
    with pytest.raises(ValueError):
        as_currency("XXX")


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("480000", Currency.USD, "480000.00"),
        ("18450.005", Currency.EUR, "18450.01"),
        ("1000.5", Currency.JPY, "1001"),
        ("1000.4", "JPY", "1000"),
        ("92000.125", Currency.CHF, "92000.13"),
    ],
)
def test_quantize_to_currency_minor_units(
    amount: str, currency: Currency | str, expected: str
) -> None:
    result = quantize(Decimal(amount), currency)
    assert result == Decimal(expected)
    assert str(result) == expected
    assert format_amount(Decimal(amount), currency) == expected


def test_is_quantized() -> None:
    assert is_quantized(Decimal("480000.00"), Currency.USD)
    assert is_quantized(Decimal("480000.0000"), Currency.USD)
    assert not is_quantized(Decimal("480000.005"), Currency.USD)
    assert is_quantized(Decimal("1500000"), Currency.JPY)
    assert not is_quantized(Decimal("1500000.5"), Currency.JPY)


def test_quantize_rejects_float() -> None:
    with pytest.raises(TypeError):
        quantize(100.0, Currency.USD)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("480000.00", Currency.USD, "480000.00"),
        ("100", Currency.EUR, "108.50"),
        ("18450.00", Currency.EUR, "20018.25"),
        ("100", Currency.GBP, "127.00"),
        ("92000", Currency.CHF, "103040.00"),
        ("1000", Currency.JPY, "6.70"),
        ("100", Currency.SGD, "74.50"),
        ("0.01", Currency.JPY, "0.00"),
        ("1234.567", Currency.EUR, "1339.51"),
    ],
)
def test_to_usd_uses_scenario_rates_rounded_to_cents(
    amount: str, currency: Currency, expected: str
) -> None:
    result = to_usd(Decimal(amount), currency)
    assert result == Decimal(expected)
    assert result.as_tuple().exponent == -2


def test_from_usd_round_trips_to_currency_minor_units() -> None:
    assert from_usd(Decimal("108.50"), Currency.EUR) == Decimal("100.00")
    assert from_usd(Decimal("6.70"), Currency.JPY) == Decimal("1000")


def test_rates_table_and_strings() -> None:
    assert rate_to_usd("EUR") == Decimal("1.0850")
    assert set(SCENARIO_RATES_TO_USD) == set(Currency)
    assert reference_rates_as_strings() == {
        "USD": "1.0000",
        "EUR": "1.0850",
        "GBP": "1.2700",
        "CHF": "1.1200",
        "JPY": "0.0067",
        "SGD": "0.7450",
    }


def test_to_usd_rejects_float() -> None:
    with pytest.raises(TypeError):
        to_usd(100.0, Currency.USD)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "minor_units_arg", "expected"),
    [
        ("480000.0000", None, "480000.00"),
        ("480000", None, "480000.00"),
        ("47.2", None, "47.20"),
        ("0.1235", None, "0.1235"),
        ("-18450.0000", None, "-18450.00"),
        ("1500000.0000", 0, "1500000"),
        ("480000.0000", 2, "480000.00"),
        ("18450.005", 2, "18450.01"),
        ("0", 2, "0.00"),
    ],
)
def test_format_money(value: str, minor_units_arg: int | None, expected: str) -> None:
    assert format_money(Decimal(value), minor_units_arg) == expected


def test_format_money_rejects_non_finite() -> None:
    with pytest.raises(ValueError):
        format_money(Decimal("NaN"))
