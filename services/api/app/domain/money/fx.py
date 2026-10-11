"""Scenario FX reference rates.

These are fixed *scenario reference rates* for the demo day, not market data. They are
used for USD equivalents on limits, risk scoring and overview totals.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.domain.money.currency import as_currency, quantize
from app.models.enums import Currency

RATES_LABEL: Final = "scenario reference rates"
RATES_AS_OF: Final = date(2026, 3, 18)
USD_QUANTUM: Final = Decimal("0.01")

SCENARIO_RATES_TO_USD: Final[Mapping[Currency, Decimal]] = {
    Currency.USD: Decimal("1"),
    Currency.EUR: Decimal("1.0850"),
    Currency.GBP: Decimal("1.2700"),
    Currency.CHF: Decimal("1.1200"),
    Currency.JPY: Decimal("0.0067"),
    Currency.SGD: Decimal("0.7450"),
}


def rate_to_usd(currency: Currency | str) -> Decimal:
    return SCENARIO_RATES_TO_USD[as_currency(currency)]


def to_usd(amount: Decimal, currency: Currency | str) -> Decimal:
    """USD equivalent of ``amount`` rounded half-up to 2 decimals."""
    if not isinstance(amount, Decimal):
        raise TypeError(f"to_usd expects Decimal, got {type(amount).__name__}")
    return (amount * rate_to_usd(currency)).quantize(USD_QUANTUM, rounding=ROUND_HALF_UP)


def from_usd(amount_usd: Decimal, currency: Currency | str) -> Decimal:
    """Convert a USD amount into ``currency`` at the scenario rate (currency minor units)."""
    if not isinstance(amount_usd, Decimal):
        raise TypeError(f"from_usd expects Decimal, got {type(amount_usd).__name__}")
    return quantize(amount_usd / rate_to_usd(currency), currency)


def reference_rates_as_strings() -> dict[str, str]:
    """Rates keyed by currency code with 4-decimal string values (API/meta payloads)."""
    return {
        currency.value: format(rate.quantize(Decimal("0.0001")), "f")
        for currency, rate in SCENARIO_RATES_TO_USD.items()
    }
