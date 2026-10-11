"""Currency minor units and quantisation (``ROUND_HALF_UP``)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.models.enums import Currency

MINOR_UNITS: Final[Mapping[Currency, int]] = {
    Currency.USD: 2,
    Currency.EUR: 2,
    Currency.GBP: 2,
    Currency.CHF: 2,
    Currency.JPY: 0,
    Currency.SGD: 2,
}

DEFAULT_MINOR_UNITS: Final = 2


def as_currency(value: Currency | str) -> Currency:
    """Coerce a currency code to :class:`Currency`, raising ``ValueError`` when unknown."""
    if isinstance(value, Currency):
        return value
    try:
        return Currency(value.strip().upper())
    except ValueError as exc:
        raise ValueError(f"Unsupported currency: {value!r}") from exc


def minor_units(currency: Currency | str) -> int:
    return MINOR_UNITS[as_currency(currency)]


def minor_units_or_none(currency: object) -> int | None:
    """Minor units for a currency-like value, or ``None`` when it is not a known currency."""
    if isinstance(currency, Currency):
        return MINOR_UNITS[currency]
    if isinstance(currency, str):
        try:
            return MINOR_UNITS[Currency(currency.strip().upper())]
        except ValueError:
            return None
    return None


def quantum(currency: Currency | str) -> Decimal:
    """The smallest representable amount, e.g. ``Decimal('0.01')`` for USD, ``1`` for JPY."""
    return Decimal(1).scaleb(-minor_units(currency))


def quantize(amount: Decimal, currency: Currency | str) -> Decimal:
    """Round ``amount`` half-up to the currency's minor units."""
    if not isinstance(amount, Decimal):
        raise TypeError(f"quantize expects Decimal, got {type(amount).__name__}")
    return amount.quantize(quantum(currency), rounding=ROUND_HALF_UP)


def is_quantized(amount: Decimal, currency: Currency | str) -> bool:
    """True when ``amount`` has no more decimals than the currency allows."""
    exponent = amount.as_tuple().exponent
    if not isinstance(exponent, int):
        return False
    return exponent >= -minor_units(currency) or amount == quantize(amount, currency)


def format_amount(amount: Decimal, currency: Currency | str) -> str:
    """Plain string with the currency's minor units, e.g. ``'480000.00'`` / ``'1500000'``."""
    return format(quantize(amount, currency), "f")
