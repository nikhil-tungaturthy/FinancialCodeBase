"""Declarative base, column types and mixins shared by every model.

SQLite has no timezone-aware datetime or exact decimal storage, so two type decorators
enforce the project's invariants at the boundary:

* :class:`UTCDateTime` stores ISO-8601 strings in UTC and always returns aware UTC
  datetimes. Naive datetimes are rejected on write.
* :class:`MoneyType` stores ``NUMERIC(18, 4)`` and always returns ``Decimal`` quantised
  to the column scale. Floats are rejected on write.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import JSON, MetaData, Numeric, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core import clock

JSONDict = dict[str, Any]
JSONList = list[Any]

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

ISO_UTC_LENGTH = 32


class UTCDateTime(TypeDecorator[datetime]):
    """Aware UTC datetime persisted as a fixed-width ISO-8601 string (sortable in SQL)."""

    impl = String(ISO_UTC_LENGTH)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"UTCDateTime expects datetime, got {type(value).__name__}")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTCDateTime refuses naive datetimes; attach a timezone")
        return value.astimezone(UTC).isoformat(timespec="microseconds")

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def process_literal_param(self, value: datetime | None, dialect: Dialect) -> str:
        bound = self.process_bind_param(value, dialect)
        return "NULL" if bound is None else f"'{bound}'"

    @property
    def python_type(self) -> type[datetime]:
        return datetime


class MoneyType(TypeDecorator[Decimal]):
    """Decimal amounts quantised to the column scale. ``MoneyType(18, 4)`` is the default.

    Python code only ever sees ``Decimal`` (floats are rejected on write). On SQLite the
    underlying ``NUMERIC`` column is stored as INTEGER/REAL, so values are exact up to about
    15 significant digits (``999,999,999.9999`` at 4 dp); every amount in the scenario is far
    below that bound. Dialects with native decimals (PostgreSQL) store the full precision.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int = 18, scale: int = 4) -> None:
        super().__init__(precision, scale, asdecimal=True)
        self.precision = precision
        self.scale = scale
        self._quantum = Decimal(1).scaleb(-scale)

    def process_bind_param(self, value: object, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, bool | float):
            raise TypeError(
                f"MoneyType refuses {type(value).__name__}; use decimal.Decimal for amounts"
            )
        if isinstance(value, Decimal):
            amount = value
        elif isinstance(value, int | str):
            amount = Decimal(value)
        else:
            raise TypeError(f"MoneyType cannot store {type(value).__name__}")
        return amount.quantize(self._quantum, rounding=ROUND_HALF_UP)

    def process_result_value(self, value: object, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            amount = value
        elif isinstance(value, float):
            amount = Decimal(repr(value))
        else:
            amount = Decimal(str(value))
        return amount.quantize(self._quantum, rounding=ROUND_HALF_UP)

    def process_literal_param(self, value: object, dialect: Dialect) -> str:
        bound = self.process_bind_param(value, dialect)
        return "NULL" if bound is None else format(bound, "f")

    @property
    def python_type(self) -> type[Decimal]:
        return Decimal


Money = MoneyType(18, 4)
MoneyUSD = MoneyType(18, 2)


def enum_type(enum_cls: type[enum.Enum], length: int = 40) -> sa.Enum:
    """A portable VARCHAR-backed enum column storing the enum *values*."""
    return sa.Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    """Declarative base with the project naming convention and type map."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: UTCDateTime(),
        Decimal: Money,
        dict[str, Any]: JSON,
        list[Any]: JSON,
        enum.Enum: sa.Enum(
            enum.Enum,
            native_enum=False,
            length=40,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
    }


class TimestampMixin:
    """``created_at`` / ``updated_at`` stamped from the scenario clock."""

    created_at: Mapped[datetime] = mapped_column(default=clock.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=clock.now, onupdate=clock.now, nullable=False
    )
