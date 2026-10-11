"""Post balanced ledger journals for a settled batch.

The poster is idempotent: a payment that already has a principal credit in the
batch is skipped. The historical variance on ``SB-20260317-SEPA-02`` predates
this guard — the posting run retried after a lock and wrote a second credit
for ``MGB-PAY-5143``. Re-running the poster now will not add a third.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core import clock
from app.core.ids import journal_ref, ledger_entry_ref
from app.models.enums import LedgerDirection, LedgerLeg, PostingSource
from app.models.ledger import LedgerEntry
from app.models.payments import Payment
from app.models.settlement import SettlementBatch


def _has_principal_credit(batch: SettlementBatch, payment_id: int) -> bool:
    return any(
        entry.payment_id == payment_id
        and entry.leg is LedgerLeg.PRINCIPAL
        and entry.direction is LedgerDirection.CREDIT
        for entry in batch.ledger_entries
    )


def post_batch_ledger(
    session: Session, batch: SettlementBatch, *, posted_at: datetime | None = None
) -> int:
    """Post missing principal and fee legs. Returns the number of payments posted."""
    moment = posted_at or clock.now()
    posted = 0
    next_ledger = _max_suffix(batch, "LE-") + 1
    next_journal = _max_suffix(batch, "JRN-") + 1
    for payment in batch.payments:
        if _has_principal_credit(batch, payment.id):
            continue
        _write_journal(session, batch, payment, journal_ref(next_journal), next_ledger, moment)
        next_journal += 1
        next_ledger += 4
        posted += 1
    return posted


def _max_suffix(batch: SettlementBatch, prefix: str) -> int:
    highest = 0
    for entry in batch.ledger_entries:
        for value in (entry.entry_ref, entry.journal_ref):
            if value.startswith(prefix):
                tail = value.removeprefix(prefix)
                if tail.isdigit():
                    highest = max(highest, int(tail))
    return highest


def _write_journal(
    session: Session,
    batch: SettlementBatch,
    payment: Payment,
    journal: str,
    start: int,
    posted_at: datetime,
) -> None:
    ccy = payment.currency.value
    legs = [
        (
            ledger_entry_ref(start),
            LedgerDirection.DEBIT,
            payment.amount,
            LedgerLeg.PRINCIPAL,
            f"1100-CUST-{ccy}",
        ),
        (
            ledger_entry_ref(start + 1),
            LedgerDirection.CREDIT,
            payment.amount,
            LedgerLeg.PRINCIPAL,
            f"2010-NOSTRO-{ccy}",
        ),
        (
            ledger_entry_ref(start + 2),
            LedgerDirection.DEBIT,
            payment.fee_amount,
            LedgerLeg.FEE,
            f"1100-CUST-{ccy}",
        ),
        (
            ledger_entry_ref(start + 3),
            LedgerDirection.CREDIT,
            payment.fee_amount,
            LedgerLeg.FEE,
            f"4100-FEE-INCOME-{ccy}",
        ),
    ]
    for entry_ref, direction, amount, leg, account in legs:
        if amount == 0:
            continue
        session.add(
            LedgerEntry(
                entry_ref=entry_ref,
                journal_ref=journal,
                payment_id=payment.id,
                batch_id=batch.id,
                account_code=account,
                direction=direction,
                amount=amount,
                currency=payment.currency,
                posted_at=posted_at,
                value_date=payment.value_date,
                description=f"{leg.value.title()} {direction.value.lower()} {payment.payment_ref}",
                posting_source=PostingSource.LEGACY_BATCH,
                leg=leg,
                correlation_id=batch.correlation_id,
            )
        )
