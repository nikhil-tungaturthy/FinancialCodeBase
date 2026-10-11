"""Daily reconciliation of settled batches.

Compares each batch's settlement entries with its principal-credit ledger rows
and records one result. Replaying the same inputs returns the existing result
instead of inserting another run.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import BatchStatus
from app.models.settlement import SettlementBatch
from app.services.workflow import reconcile


def reconcile_value_date(session: Session, value_date: date, *, actor: str = "system") -> int:
    """Reconcile every settled batch on ``value_date``. Returns the number of batches visited."""
    batches = (
        session.scalars(
            select(SettlementBatch)
            .where(
                SettlementBatch.value_date == value_date,
                SettlementBatch.status.in_(
                    [BatchStatus.SETTLED, BatchStatus.DISCREPANCY, BatchStatus.RECONCILED]
                ),
            )
            .options(
                selectinload(SettlementBatch.entries),
                selectinload(SettlementBatch.ledger_entries),
                selectinload(SettlementBatch.reconciliation_results),
            )
        )
        .unique()
        .all()
    )
    for batch in batches:
        reconcile(session, batch, actor=actor, notes="Daily reconciliation")
    return len(batches)
