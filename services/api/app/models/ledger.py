"""General ledger postings produced by the payment engine, fee engine and batch jobs."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Currency, LedgerDirection, LedgerLeg, PostingSource

if TYPE_CHECKING:
    from app.models.payments import Payment
    from app.models.settlement import SettlementBatch


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_entries_batch_leg_direction", "batch_id", "leg", "direction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    journal_ref: Mapped[str] = mapped_column(String(16), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_batches.id"), index=True)
    account_code: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[LedgerDirection]
    amount: Mapped[Decimal]
    currency: Mapped[Currency]
    posted_at: Mapped[datetime] = mapped_column(index=True)
    value_date: Mapped[date]
    description: Mapped[str] = mapped_column(String(280))
    posting_source: Mapped[PostingSource]
    leg: Mapped[LedgerLeg]
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)

    payment: Mapped[Payment | None] = relationship(back_populates="ledger_entries")
    batch: Mapped[SettlementBatch | None] = relationship(back_populates="ledger_entries")

    def __repr__(self) -> str:
        return (
            f"LedgerEntry(ref={self.entry_ref!r}, {self.direction.value} "
            f"{self.amount} {self.currency.value} {self.account_code})"
        )
