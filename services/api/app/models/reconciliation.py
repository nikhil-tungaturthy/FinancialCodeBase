"""Reconciliation runs recorded against a settlement batch."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONList
from app.models.enums import ReconciliationStatus

if TYPE_CHECKING:
    from app.models.settlement import SettlementBatch


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_ref: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("settlement_batches.id"), index=True)
    run_at: Mapped[datetime] = mapped_column(index=True)
    status: Mapped[ReconciliationStatus]
    matched_count: Mapped[int] = mapped_column(default=0)
    unmatched_count: Mapped[int] = mapped_column(default=0)
    expected_total: Mapped[Decimal]
    recorded_total: Mapped[Decimal]
    variance: Mapped[Decimal]
    unmatched_refs: Mapped[JSONList] = mapped_column(default=list)
    discrepancies: Mapped[JSONList] = mapped_column(default=list)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    batch: Mapped[SettlementBatch] = relationship(back_populates="reconciliation_results")

    def __repr__(self) -> str:
        return f"ReconciliationResult(ref={self.run_ref!r}, status={self.status.value})"
