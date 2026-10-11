"""Fee schedules for the modern fee engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Currency, CustomerSegment, FeeSource, FeeType, Rail


class FeeSchedule(Base):
    __tablename__ = "fee_schedules"
    __table_args__ = (
        Index("ix_fee_schedules_rail_currency_segment", "rail", "currency", "segment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rail: Mapped[Rail]
    currency: Mapped[Currency]
    segment: Mapped[CustomerSegment]
    fee_type: Mapped[FeeType]
    flat_amount: Mapped[Decimal]
    bps: Mapped[int] = mapped_column(default=0)
    min_fee: Mapped[Decimal]
    max_fee: Mapped[Decimal | None]
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    source: Mapped[FeeSource] = mapped_column(default=FeeSource.MODERN)
