"""Explicit decimal rounding helpers. Floats never enter money arithmetic."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
ONE = Decimal("1")
BASIS_POINT_DIVISOR = Decimal("10000")


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert an exact representation to ``Decimal``; floats are rejected."""
    if isinstance(value, bool | float):
        raise TypeError(
            f"Refusing to build a money amount from {type(value).__name__}; pass str or Decimal"
        )
    if isinstance(value, Decimal):
        return value
    return Decimal(value)


def round_half_up(amount: Decimal, places: int) -> Decimal:
    """Round ``amount`` to ``places`` decimals using ``ROUND_HALF_UP``."""
    if not isinstance(amount, Decimal):
        raise TypeError(f"round_half_up expects Decimal, got {type(amount).__name__}")
    if places < 0:
        raise ValueError("places must be zero or positive")
    return amount.quantize(ONE.scaleb(-places), rounding=ROUND_HALF_UP)


def apply_basis_points(amount: Decimal, bps: Decimal | int, places: int = 2) -> Decimal:
    """``amount * bps / 10,000`` rounded half-up to ``places`` decimals."""
    factor = to_decimal(bps) / BASIS_POINT_DIVISOR
    return round_half_up(amount * factor, places)
