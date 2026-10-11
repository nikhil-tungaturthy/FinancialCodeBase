"""Settlement batches (one per rail and value date window) and their entries."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import BatchStatus, Currency, Rail, SettlementEntryStatus

if TYPE_CHECKING:
    from app.models.ledger import LedgerEntry
    from app.models.payments import Payment
    from app.models.reconciliation import ReconciliationResult


class SettlementBatch(TimestampMixin, Base):
    __tablename__ = "settlement_batches"
    __table_args__ = (Index("ix_settlement_batches_rail_value_date", "rail", "value_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    rail: Mapped[Rail]
    currency: Mapped[Currency]
    value_date: Mapped[date]
    window_key: Mapped[str] = mapped_column(String(40), index=True)
    timezone: Mapped[str] = mapped_column(String(48))
    cutoff_at: Mapped[datetime]
    status: Mapped[BatchStatus] = mapped_column(index=True)
    expected_total: Mapped[Decimal]
    recorded_total: Mapped[Decimal | None]
    entry_count: Mapped[int] = mapped_column(default=0)
    submitted_at: Mapped[datetime | None]
    settled_at: Mapped[datetime | None]
    reconciled_at: Mapped[datetime | None]
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)

    entries: Mapped[list[SettlementEntry]] = relationship(
        back_populates="batch", order_by="SettlementEntry.sequence", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="settlement_batch")
    ledger_entries: Mapped[list[LedgerEntry]] = relationship(back_populates="batch")
    reconciliation_results: Mapped[list[ReconciliationResult]] = relationship(
        back_populates="batch", order_by="ReconciliationResult.run_at"
    )

    def __repr__(self) -> str:
        return f"SettlementBatch(ref={self.batch_ref!r}, status={self.status.value})"


class SettlementEntry(Base):
    __tablename__ = "settlement_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("settlement_batches.id"), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), index=True)
    amount: Mapped[Decimal]
    currency: Mapped[Currency]
    status: Mapped[SettlementEntryStatus] = mapped_column(default=SettlementEntryStatus.PENDING)
    external_reference: Mapped[str | None] = mapped_column(String(64))
    settled_at: Mapped[datetime | None]
    sequence: Mapped[int]

    batch: Mapped[SettlementBatch] = relationship(back_populates="entries")
    payment: Mapped[Payment | None] = relationship(back_populates="settlement_entries")

    def __repr__(self) -> str:
        return f"SettlementEntry(ref={self.entry_ref!r}, status={self.status.value})"
