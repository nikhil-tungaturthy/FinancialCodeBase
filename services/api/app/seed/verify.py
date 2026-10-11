"""Invariants the scenario seed must keep holding."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.ids import exception_ref, payment_ref
from app.db.init import SEED_VERSION_KEY, get_seed_metadata
from app.domain.fees.service import compute_fee
from app.models.enums import (
    ExceptionStatus,
    LedgerDirection,
    PaymentStatus,
    ReconciliationStatus,
)
from app.models.exceptions import PaymentException
from app.models.ledger import LedgerEntry
from app.models.payments import Payment, PaymentEvent
from app.models.settlement import SettlementBatch
from app.seed.build import DISCREPANCY_BATCH, HERO_EXCEPTION_NUMBER, HERO_NUMBER, SEED_VERSION

OPEN = {
    ExceptionStatus.OPEN,
    ExceptionStatus.IN_REVIEW,
    ExceptionStatus.PENDING_APPROVAL,
    ExceptionStatus.ESCALATED,
}


def verify_seed(session: Session) -> list[str]:
    """Return human-readable failures. An empty list means the seed is consistent."""
    problems: list[str] = []
    version = get_seed_metadata(session, SEED_VERSION_KEY)
    if version != SEED_VERSION:
        problems.append(f"seed_version is {version!r}, expected {SEED_VERSION}")

    hero = session.scalar(select(Payment).where(Payment.payment_ref == payment_ref(HERO_NUMBER)))
    if hero is None:
        problems.append("hero payment MGB-PAY-1042 is missing")
    else:
        if hero.status is not PaymentStatus.HELD:
            problems.append(f"hero status is {hero.status.value}")
        if hero.amount != Decimal("480000.0000") and hero.amount != Decimal("480000.00"):
            problems.append(f"hero amount is {hero.amount}")
        quote = compute_fee(hero.rail, hero.currency, hero.customer.segment, Decimal("480000.00"))
        if quote.amount != Decimal("47.20"):
            problems.append(f"hero fee quote is {quote.amount}, expected 47.20")
        if hero.fee_amount != Decimal("47.2000") and hero.fee_amount != Decimal("47.20"):
            problems.append(f"hero stored fee is {hero.fee_amount}")

    hero_exception = session.scalar(
        select(PaymentException).where(
            PaymentException.exception_ref == exception_ref(HERO_EXCEPTION_NUMBER)
        )
    )
    if hero_exception is None:
        problems.append("hero exception MGB-EXC-0231 is missing")
    else:
        if hero_exception.queue != "INST-HV":
            problems.append(f"hero queue is {hero_exception.queue}")
        if hero_exception.severity.value != "HIGH":
            problems.append(f"hero severity is {hero_exception.severity.value}")
        if hero_exception.reason_code != "BENEFICIARY_NAME_MISMATCH":
            problems.append(f"hero reason is {hero_exception.reason_code}")
        if hero_exception.due_by is not None and hero_exception.due_by < hero_exception.opened_at:
            problems.append("hero due_by is before opened_at")

    batch = session.scalar(
        select(SettlementBatch)
        .where(SettlementBatch.batch_ref == DISCREPANCY_BATCH)
        .options(selectinload(SettlementBatch.reconciliation_results))
    )
    if batch is None:
        problems.append(f"{DISCREPANCY_BATCH} is missing")
    else:
        if batch.expected_total != Decimal("235367.0000") and batch.expected_total != Decimal(
            "235367.00"
        ):
            problems.append(f"discrepancy expected_total is {batch.expected_total}")
        if batch.recorded_total != Decimal("253817.0000") and batch.recorded_total != Decimal(
            "253817.00"
        ):
            problems.append(f"discrepancy recorded_total is {batch.recorded_total}")
        latest = batch.reconciliation_results[-1] if batch.reconciliation_results else None
        if latest is None or latest.run_ref != "RR-000061":
            problems.append("discrepancy reconciliation RR-000061 is missing")
        elif latest.status is not ReconciliationStatus.UNMATCHED or (
            latest.variance != Decimal("18450.0000") and latest.variance != Decimal("18450.00")
        ):
            problems.append(
                f"discrepancy reconciliation is {latest.status.value} variance {latest.variance}"
            )

    held_without = session.scalars(
        select(Payment.payment_ref)
        .where(Payment.status == PaymentStatus.HELD)
        .where(~Payment.exceptions.any(PaymentException.status.in_(tuple(OPEN))))
    ).all()
    if held_without:
        problems.append(f"held payments without an open exception: {list(held_without)[:5]}")

    journals = session.execute(
        select(
            LedgerEntry.journal_ref,
            LedgerEntry.direction,
            func.sum(LedgerEntry.amount),
        ).group_by(LedgerEntry.journal_ref, LedgerEntry.direction)
    ).all()
    totals: dict[str, dict[str, Decimal]] = {}
    for journal_ref, direction, amount in journals:
        totals.setdefault(journal_ref, {})[direction.value] = Decimal(amount)
    for journal_ref, sides in totals.items():
        debit = sides.get(LedgerDirection.DEBIT.value, Decimal("0"))
        credit = sides.get(LedgerDirection.CREDIT.value, Decimal("0"))
        if debit != credit:
            problems.append(f"journal {journal_ref} is unbalanced ({debit} vs {credit})")
            break

    broken = session.execute(
        select(
            PaymentEvent.payment_id,
            func.count(),
            func.min(PaymentEvent.sequence),
            func.max(PaymentEvent.sequence),
        ).group_by(PaymentEvent.payment_id)
    ).all()
    for _payment_id, count, low, high in broken:
        if low != 1 or high != count:
            problems.append("a payment has a non-contiguous event sequence")
            break

    return problems
