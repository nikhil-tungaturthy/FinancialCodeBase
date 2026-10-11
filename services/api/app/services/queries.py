"""Read-side queries for the API."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit.actions import AuditAction
from app.core import clock
from app.core.errors import NotFoundError
from app.db.init import SEED_VERSION_KEY, get_seed_metadata
from app.domain.money.fx import RATES_LABEL, reference_rates_as_strings
from app.domain.policies.reasons import load_exception_policy
from app.domain.settlement.calendar import WEEKDAY_CODES
from app.domain.settlement.cutoff import all_window_statuses, load_cutoff_policies
from app.models.approvals import ApprovalRequest
from app.models.audit import AuditEvent
from app.models.customers import Beneficiary, Customer
from app.models.enums import (
    BatchStatus,
    Currency,
    ExceptionSeverity,
    ExceptionStatus,
    IncidentStatus,
    PaymentStatus,
    Rail,
)
from app.models.exceptions import ExceptionAssignment, ExceptionResolution, PaymentException
from app.models.fees import FeeSchedule
from app.models.incidents import OperationalIncident
from app.models.ledger import LedgerEntry
from app.models.payments import Payment
from app.models.rules import BusinessRule
from app.models.settlement import SettlementBatch, SettlementEntry
from app.models.users import User
from app.schemas.approvals import ApprovalDecisionOut, ApprovalDetail, ApprovalSummary
from app.schemas.audit import AuditActionsResponse, AuditEventOut
from app.schemas.common import Page
from app.schemas.exceptions import ExceptionDetail, ExceptionQueueItem, ExceptionSummaryResponse
from app.schemas.incidents import IncidentDetail, IncidentOut
from app.schemas.ledger import LedgerEntryOut
from app.schemas.meta import ScenarioMeta
from app.schemas.overview import (
    CurrencyValue,
    HighPriorityItem,
    OverviewResponse,
    QuickLink,
    TrendPoint,
)
from app.schemas.payments import PaymentDetail, PaymentSummary
from app.schemas.policies import (
    BusinessRuleOut,
    ExceptionPolicyDocument,
    FeeScheduleOut,
    SettlementCutoffPolicy,
    SettlementCutoffPolicyDocument,
)
from app.schemas.settlement import (
    BatchDetail,
    BatchSummary,
    CurrencyVariance,
    ReconciliationSummary,
    SettlementWindowsResponse,
    SettlementWindowStatus,
    WindowState,
)
from app.schemas.users import UserOut
from app.services.present import (
    OPEN_EXCEPTION_STATUSES,
    approval_summary,
    audit_out,
    batch_detail,
    batch_summary,
    can_decide,
    exception_detail,
    exception_queue_item,
    ledger_out,
    payment_detail,
    payment_summary,
)
from app.services.workflow import (
    approval_link,
    available_actions,
    available_operations,
    timeline_for,
)

_PAYMENT_LIST = (
    joinedload(Payment.customer),
    joinedload(Payment.beneficiary),
    selectinload(Payment.exceptions),
)
_PAYMENT_DETAIL = (
    joinedload(Payment.customer),
    joinedload(Payment.debit_account),
    joinedload(Payment.beneficiary),
    joinedload(Payment.instruction),
    selectinload(Payment.events),
    selectinload(Payment.validation_results),
    selectinload(Payment.exceptions),
    joinedload(Payment.settlement_batch),
)


def _count(session: Session, stmt: Select[Any]) -> int:
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    return int(total or 0)


def _day_bounds(value: date) -> tuple[datetime, datetime]:
    start = datetime.combine(value, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


def scenario_meta(session: Session) -> ScenarioMeta:
    moment = clock.now()
    return ScenarioMeta(
        scenario_now=moment,
        scenario_date=moment.date(),
        business_day_label=moment.strftime("%a %d %b %Y"),
        seed_version=get_seed_metadata(session, SEED_VERSION_KEY),
        display_timezone="UTC",
        fx_reference_rates=reference_rates_as_strings(),
        fx_rates_label=RATES_LABEL,
        environment="demo",
    )


def list_users(session: Session, *, include_inactive: bool = False) -> Page[UserOut]:
    stmt = select(User)
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    stmt = stmt.order_by(User.username)
    rows = session.scalars(stmt).all()
    items = [UserOut.model_validate(row) for row in rows]
    return Page.build(items, page=1, page_size=max(len(items), 1), total=len(items))


def current_user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


def list_payments(
    session: Session,
    *,
    search: str | None,
    statuses: list[PaymentStatus] | None,
    rails: list[Rail] | None,
    currencies: list[str] | None,
    priorities: list[str] | None,
    risk_tiers: list[str] | None,
    date_from: date | None,
    date_to: date | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> Page[PaymentSummary]:
    stmt: Select[tuple[Payment]] = select(Payment).join(Payment.customer).join(Payment.beneficiary)
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Payment.payment_ref.ilike(like),
                Payment.end_to_end_reference.ilike(like),
                Customer.legal_name.ilike(like),
                Beneficiary.name.ilike(like),
            )
        )
    if statuses:
        stmt = stmt.where(Payment.status.in_(statuses))
    if rails:
        stmt = stmt.where(Payment.rail.in_(rails))
    if currencies:
        stmt = stmt.where(Payment.currency.in_(currencies))
    if priorities:
        stmt = stmt.where(Payment.priority.in_(priorities))
    if risk_tiers:
        stmt = stmt.where(Payment.risk_tier.in_(risk_tiers))
    if date_from is not None:
        stmt = stmt.where(Payment.created_at >= _day_bounds(date_from)[0])
    if date_to is not None:
        stmt = stmt.where(Payment.created_at < _day_bounds(date_to)[1])
    sort_columns = {
        "created_at": Payment.created_at,
        "amount": Payment.amount,
        "status": Payment.status,
        "payment_ref": Payment.payment_ref,
        "customer": Customer.legal_name,
    }
    column = sort_columns.get(sort, Payment.created_at)
    stmt = stmt.order_by(column.asc() if order == "asc" else column.desc(), Payment.id.asc())
    total = _count(session, stmt)
    rows = (
        session.scalars(
            stmt.options(*_PAYMENT_LIST).offset((page - 1) * page_size).limit(page_size)
        )
        .unique()
        .all()
    )
    return Page.build(
        [payment_summary(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def get_payment(session: Session, payment_ref: str, user: User) -> PaymentDetail:
    payment = (
        session.scalars(
            select(Payment).where(Payment.payment_ref == payment_ref).options(*_PAYMENT_DETAIL)
        )
        .unique()
        .one_or_none()
    )
    if payment is None:
        raise NotFoundError.for_entity("payment", payment_ref)
    audits = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_ref == payment.payment_ref)
        .order_by(AuditEvent.occurred_at)
    ).all()
    return payment_detail(payment, list(audits), available_operations(user, payment))


def list_exceptions(
    session: Session,
    *,
    statuses: list[ExceptionStatus] | None,
    severities: list[ExceptionSeverity] | None,
    assigned_to: str | None,
    queue: str | None,
    search: str | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> Page[ExceptionQueueItem]:
    stmt = (
        select(PaymentException)
        .join(PaymentException.payment)
        .join(Payment.customer)
        .join(Payment.beneficiary)
    )
    if statuses:
        stmt = stmt.where(PaymentException.status.in_(statuses))
    if severities:
        stmt = stmt.where(PaymentException.severity.in_(severities))
    if assigned_to:
        stmt = stmt.join(PaymentException.assigned_to).where(User.username == assigned_to)
    if queue:
        stmt = stmt.where(PaymentException.queue == queue)
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                PaymentException.exception_ref.ilike(like),
                PaymentException.reason_code.ilike(like),
                Payment.payment_ref.ilike(like),
                Customer.legal_name.ilike(like),
            )
        )
    severity_rank = case(
        (PaymentException.severity == ExceptionSeverity.CRITICAL, 4),
        (PaymentException.severity == ExceptionSeverity.HIGH, 3),
        (PaymentException.severity == ExceptionSeverity.MEDIUM, 2),
        else_=1,
    )
    sort_columns = {
        "opened_at": PaymentException.opened_at,
        "due_by": PaymentException.due_by,
        "severity": severity_rank,
        "amount": Payment.usd_equivalent,
        "exception_ref": PaymentException.exception_ref,
        "status": PaymentException.status,
    }
    column = sort_columns.get(sort, PaymentException.due_by)
    stmt = stmt.order_by(
        column.asc() if order == "asc" else column.desc(), PaymentException.id.asc()
    )
    total = _count(session, stmt)
    rows = (
        session.scalars(
            stmt.options(
                joinedload(PaymentException.payment).joinedload(Payment.customer),
                joinedload(PaymentException.payment).joinedload(Payment.beneficiary),
                joinedload(PaymentException.payment).selectinload(Payment.exceptions),
                joinedload(PaymentException.assigned_to),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return Page.build(
        [exception_queue_item(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def exception_summary(session: Session) -> ExceptionSummaryResponse:
    rows = session.execute(
        select(
            PaymentException.status, PaymentException.severity, PaymentException.queue, func.count()
        ).group_by(PaymentException.status, PaymentException.severity, PaymentException.queue)
    ).all()
    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_queue: dict[str, int] = {}
    total_open = 0
    for status, severity, queue, count in rows:
        by_status[status.value] = by_status.get(status.value, 0) + count
        by_severity[severity.value] = by_severity.get(severity.value, 0) + count
        by_queue[queue] = by_queue.get(queue, 0) + count
        if status in OPEN_EXCEPTION_STATUSES:
            total_open += count
    return ExceptionSummaryResponse(
        total_open=total_open,
        by_status=by_status,
        by_severity=by_severity,
        by_queue=by_queue,
    )


def get_exception(session: Session, exception_ref: str, user: User) -> ExceptionDetail:
    item = (
        session.scalars(
            select(PaymentException)
            .where(PaymentException.exception_ref == exception_ref)
            .options(
                joinedload(PaymentException.payment).joinedload(Payment.customer),
                joinedload(PaymentException.payment).joinedload(Payment.beneficiary),
                joinedload(PaymentException.payment).joinedload(Payment.instruction),
                joinedload(PaymentException.payment).selectinload(Payment.validation_results),
                joinedload(PaymentException.payment).selectinload(Payment.events),
                joinedload(PaymentException.payment).selectinload(Payment.exceptions),
                joinedload(PaymentException.assigned_to),
                selectinload(PaymentException.notes),
                selectinload(PaymentException.assignments).joinedload(
                    ExceptionAssignment.assigned_to
                ),
                selectinload(PaymentException.resolutions).joinedload(
                    ExceptionResolution.approval_request
                ),
            )
        )
        .unique()
        .one_or_none()
    )
    if item is None:
        raise NotFoundError.for_entity("exception", exception_ref)
    audits = list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_ref.in_([item.exception_ref, item.payment.payment_ref]))
            .order_by(AuditEvent.occurred_at)
        ).all()
    )
    return exception_detail(
        item,
        timeline_for(item, audits),
        available_actions(user, item),
        approval_link(item),
    )


def list_batches(
    session: Session,
    *,
    statuses: list[BatchStatus] | None,
    rails: list[Rail] | None,
    value_date: date | None,
    page: int,
    page_size: int,
) -> Page[BatchSummary]:
    stmt = select(SettlementBatch)
    if statuses:
        stmt = stmt.where(SettlementBatch.status.in_(statuses))
    if rails:
        stmt = stmt.where(SettlementBatch.rail.in_(rails))
    if value_date is not None:
        stmt = stmt.where(SettlementBatch.value_date == value_date)
    stmt = stmt.order_by(SettlementBatch.value_date.desc(), SettlementBatch.batch_ref.asc())
    total = _count(session, stmt)
    rows = (
        session.scalars(
            stmt.options(selectinload(SettlementBatch.reconciliation_results))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return Page.build(
        [batch_summary(row) for row in rows], page=page, page_size=page_size, total=total
    )


def get_batch(session: Session, batch_ref: str) -> BatchDetail:
    batch = (
        session.scalars(
            select(SettlementBatch)
            .where(SettlementBatch.batch_ref == batch_ref)
            .options(
                selectinload(SettlementBatch.entries).joinedload(SettlementEntry.payment),
                selectinload(SettlementBatch.ledger_entries).joinedload(LedgerEntry.payment),
                selectinload(SettlementBatch.ledger_entries).joinedload(LedgerEntry.batch),
                selectinload(SettlementBatch.reconciliation_results),
                selectinload(SettlementBatch.payments),
            )
        )
        .unique()
        .one_or_none()
    )
    if batch is None:
        raise NotFoundError.for_entity("settlement batch", batch_ref)
    return batch_detail(batch)


def settlement_windows(session: Session) -> SettlementWindowsResponse:
    now = clock.now()
    windows: list[SettlementWindowStatus] = []
    for status in all_window_statuses(now):
        key = status.current_window.window_key
        currency = Currency(status.currency) if status.currency else Currency.USD
        pending = session.execute(
            select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.settlement_window_key == key,
                Payment.status.in_(
                    [
                        PaymentStatus.APPROVED,
                        PaymentStatus.PROCESSING,
                        PaymentStatus.PENDING_SETTLEMENT,
                        PaymentStatus.HELD,
                    ]
                ),
                Payment.currency == currency,
            )
        ).one()
        windows.append(
            SettlementWindowStatus(
                rail=Rail(status.rail),
                currency=currency,
                timezone=status.timezone,
                cutoff_local=status.cutoff_local,
                cutoff_at=status.current_window.cutoff_at,
                status=cast(WindowState, status.status),
                minutes_to_cutoff=status.minutes_to_cutoff,
                next_window_key=status.next_window.window_key,
                pending_count=int(pending[0] or 0),
                pending_value=Decimal(pending[1]),
            )
        )
    return SettlementWindowsResponse(as_of=now, windows=windows)


def reconciliation_summary(session: Session) -> ReconciliationSummary:
    batches = (
        session.scalars(
            select(SettlementBatch).options(selectinload(SettlementBatch.reconciliation_results))
        )
        .unique()
        .all()
    )
    by_status: dict[str, int] = {}
    variances: dict[str, tuple[Decimal, int]] = {}
    open_rows: list[BatchSummary] = []
    for batch in batches:
        by_status[batch.status.value] = by_status.get(batch.status.value, 0) + 1
        if batch.recorded_total is not None and batch.recorded_total != batch.expected_total:
            current, count = variances.get(batch.currency.value, (Decimal("0"), 0))
            variances[batch.currency.value] = (
                current + (batch.recorded_total - batch.expected_total),
                count + 1,
            )
        if batch.status is BatchStatus.DISCREPANCY:
            open_rows.append(batch_summary(batch))
    return ReconciliationSummary(
        batches_total=len(batches),
        by_status=by_status,
        total_variance_by_currency=[
            CurrencyVariance(currency=Currency(currency), variance=amount, batch_count=count)
            for currency, (amount, count) in sorted(variances.items())
        ],
        open_discrepancies=open_rows,
    )


def list_ledger(
    session: Session,
    *,
    payment_ref: str | None,
    batch_ref: str | None,
    journal_ref: str | None,
    page: int,
    page_size: int,
) -> Page[LedgerEntryOut]:
    stmt = select(LedgerEntry)
    if payment_ref:
        stmt = stmt.join(LedgerEntry.payment).where(Payment.payment_ref == payment_ref)
    if batch_ref:
        stmt = stmt.join(LedgerEntry.batch).where(SettlementBatch.batch_ref == batch_ref)
    if journal_ref:
        stmt = stmt.where(LedgerEntry.journal_ref == journal_ref)
    stmt = stmt.order_by(LedgerEntry.posted_at, LedgerEntry.entry_ref)
    total = _count(session, stmt)
    rows = (
        session.scalars(
            stmt.options(joinedload(LedgerEntry.payment), joinedload(LedgerEntry.batch))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return Page.build(
        [ledger_out(row) for row in rows], page=page, page_size=page_size, total=total
    )


def list_approvals(
    session: Session,
    *,
    statuses: list[str] | None,
    page: int,
    page_size: int,
) -> Page[ApprovalSummary]:
    stmt = select(ApprovalRequest)
    if statuses:
        stmt = stmt.where(ApprovalRequest.status.in_(statuses))
    stmt = stmt.order_by(ApprovalRequest.created_at.desc())
    total = _count(session, stmt)
    rows = (
        session.scalars(
            stmt.options(selectinload(ApprovalRequest.decisions))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    users = {user.username: user for user in session.scalars(select(User)).all()}
    items = []
    for row in rows:
        requester = users.get(row.requested_by)
        if requester is None:
            continue
        items.append(approval_summary(row, requester))
    return Page.build(items, page=page, page_size=page_size, total=total)


def get_approval(session: Session, approval_ref: str, user: User) -> ApprovalDetail:
    approval = (
        session.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.approval_ref == approval_ref)
            .options(selectinload(ApprovalRequest.decisions))
        )
        .unique()
        .one_or_none()
    )
    if approval is None:
        raise NotFoundError.for_entity("approval", approval_ref)
    requester = session.scalar(select(User).where(User.username == approval.requested_by))
    if requester is None:
        raise NotFoundError.for_entity("user", approval.requested_by)
    summary = approval_summary(approval, requester)
    decisions = [
        ApprovalDecisionOut(
            decided_by=row.decided_by,
            decision=row.decision,
            rationale=row.rationale,
            decided_at=row.decided_at,
        )
        for row in approval.decisions
    ]
    return ApprovalDetail(
        **summary.model_dump(),
        justification=approval.justification,
        decisions=decisions,
        can_decide=can_decide(approval, user, requester.username),
    )


def list_audit(
    session: Session,
    *,
    entity_type: str | None,
    entity_ref: str | None,
    action: str | None,
    actor: str | None,
    correlation_id: str | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
    page: int,
    page_size: int,
) -> Page[AuditEventOut]:
    stmt = select(AuditEvent)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_ref:
        stmt = stmt.where(AuditEvent.entity_ref == entity_ref)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    if correlation_id:
        stmt = stmt.where(AuditEvent.correlation_id == correlation_id)
    if date_from is not None:
        stmt = stmt.where(AuditEvent.occurred_at >= _day_bounds(date_from)[0])
    if date_to is not None:
        stmt = stmt.where(AuditEvent.occurred_at < _day_bounds(date_to)[1])
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                AuditEvent.summary.ilike(like),
                AuditEvent.entity_ref.ilike(like),
                AuditEvent.actor.ilike(like),
            )
        )
    stmt = stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    total = _count(session, stmt)
    rows = session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return Page.build([audit_out(row) for row in rows], page=page, page_size=page_size, total=total)


def audit_actions() -> AuditActionsResponse:
    return AuditActionsResponse(items=[item.value for item in AuditAction])


def get_audit_event(session: Session, event_id: str) -> AuditEventOut:
    event = session.scalar(select(AuditEvent).where(AuditEvent.event_id == event_id))
    if event is None:
        raise NotFoundError.for_entity("audit event", event_id)
    return audit_out(event)


def list_incidents(session: Session) -> list[IncidentOut]:
    rows = session.scalars(
        select(OperationalIncident).order_by(OperationalIncident.opened_at.desc())
    ).all()
    return [IncidentOut.model_validate(row) for row in rows]


def get_incident(session: Session, incident_ref: str) -> IncidentDetail:
    row = session.scalar(
        select(OperationalIncident).where(OperationalIncident.incident_ref == incident_ref)
    )
    if row is None:
        raise NotFoundError.for_entity("incident", incident_ref)
    detail = IncidentDetail.model_validate(row)
    detail.evidence_files = ["incident.json", "settlement-run.jsonl", "reconciliation-run.jsonl"]
    return detail


def overview(session: Session, on: date) -> OverviewResponse:
    start, end = _day_bounds(on)
    created = session.scalars(
        select(Payment).where(Payment.created_at >= start, Payment.created_at < end)
    ).all()
    counted = [
        row
        for row in created
        if row.status not in {PaymentStatus.CANCELLED, PaymentStatus.REJECTED}
    ]
    by_currency: dict[str, tuple[Decimal, int]] = {}
    processed_usd = Decimal("0")
    for row in counted:
        processed_usd += row.usd_equivalent
        amount, count = by_currency.get(row.currency.value, (Decimal("0"), 0))
        by_currency[row.currency.value] = (amount + row.amount, count + 1)
    pending_rows = session.scalars(
        select(Payment).where(Payment.status == PaymentStatus.PENDING_SETTLEMENT)
    ).all()
    pending_usd = sum((row.usd_equivalent for row in pending_rows), Decimal("0"))
    open_items = (
        session.scalars(
            select(PaymentException)
            .where(PaymentException.status.in_(tuple(OPEN_EXCEPTION_STATUSES)))
            .options(joinedload(PaymentException.payment))
        )
        .unique()
        .all()
    )
    by_severity: dict[str, int] = {}
    for item in open_items:
        by_severity[item.severity.value] = by_severity.get(item.severity.value, 0) + 1
    high = [
        item
        for item in open_items
        if item.severity in {ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL}
    ]
    high.sort(key=lambda item: item.due_by or item.opened_at)
    incidents = session.scalars(
        select(OperationalIncident).where(
            OperationalIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING])
        )
    ).all()
    priority: list[HighPriorityItem] = []
    for incident in incidents:
        priority.append(
            HighPriorityItem(
                kind="INCIDENT",
                ref=incident.incident_ref,
                title=incident.title,
                severity=incident.severity.value,
                due_by=None,
                href=f"/settlement/batches/{incident.affected_batch_ref}"
                if incident.affected_batch_ref
                else "/settlement",
            )
        )
    for item in high[:6]:
        priority.append(
            HighPriorityItem(
                kind="EXCEPTION",
                ref=item.exception_ref,
                title=f"{item.reason_title} · {item.payment.payment_ref}",
                severity=item.severity.value,
                due_by=item.due_by,
                href=f"/exceptions/{item.exception_ref}",
            )
        )
    trend: list[TrendPoint] = []
    for offset in range(7, -1, -1):
        day = on - timedelta(days=offset)
        day_start, day_end = _day_bounds(day)
        day_rows = (
            [row for row in created if day_start <= row.created_at < day_end]
            if offset == 0
            else None
        )
        if day_rows is None:
            day_rows = list(
                session.scalars(
                    select(Payment).where(
                        Payment.created_at >= day_start, Payment.created_at < day_end
                    )
                ).all()
            )
        trend.append(
            TrendPoint(
                date=day,
                count=len(day_rows),
                value_usd=sum((row.usd_equivalent for row in day_rows), Decimal("0")),
                exception_count=sum(1 for row in day_rows if row.status is PaymentStatus.HELD),
            )
        )
    recent = session.scalars(
        select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(8)
    ).all()
    pending_approvals = session.scalar(
        select(func.count()).select_from(ApprovalRequest).where(ApprovalRequest.status == "PENDING")
    )
    discrepancies = session.scalar(
        select(func.count())
        .select_from(SettlementBatch)
        .where(SettlementBatch.status == BatchStatus.DISCREPANCY)
    )
    windows = settlement_windows(session).windows
    return OverviewResponse(
        date=on,
        processed_count=len(counted),
        processed_value_usd=processed_usd,
        processed_value_by_currency=[
            CurrencyValue(currency=code, amount=amount, count=count)
            for code, (amount, count) in sorted(by_currency.items())
        ],
        pending_settlement_value_usd=pending_usd,
        pending_settlement_count=len(pending_rows),
        exceptions_open_count=len(open_items),
        exceptions_by_severity=by_severity,
        high_priority_issue_count=len(priority),
        high_priority_items=priority[:8],
        settlement_windows=windows,
        trend=trend,
        recent_events=[audit_out(row) for row in reversed(list(recent))],
        quick_links=[
            QuickLink(label="Open exceptions", href="/exceptions", count=len(open_items)),
            QuickLink(
                label="Held payments",
                href="/payments?status=HELD",
                count=sum(1 for row in open_items if row.payment.status is PaymentStatus.HELD),
            ),
            QuickLink(label="Approvals", href="/approvals", count=int(pending_approvals or 0)),
            QuickLink(
                label="Discrepancies",
                href="/settlement?status=DISCREPANCY",
                count=int(discrepancies or 0),
            ),
        ],
    )


def exception_policy() -> ExceptionPolicyDocument:
    return load_exception_policy()


def cutoff_policy() -> SettlementCutoffPolicyDocument:
    document = load_cutoff_policies()
    rails = []
    for policy in document.values():
        rails.append(
            SettlementCutoffPolicy(
                rail=Rail(policy.rail),
                currency=Currency(policy.currency) if policy.currency else Currency.USD,
                timezone=policy.timezone,
                cutoff_local=f"{policy.cutoff_local_time:%H:%M}",
                value_date_offset_days=policy.value_date_offset_business_days,
                business_days=[
                    WEEKDAY_CODES[index] for index in sorted(policy.calendar.business_weekdays)
                ],
                holidays=sorted(policy.calendar.holidays),
            )
        )
    return SettlementCutoffPolicyDocument(version="2026.03", rails=rails)


def list_rules(session: Session) -> list[BusinessRuleOut]:
    rows = session.scalars(select(BusinessRule).order_by(BusinessRule.rule_code)).all()
    return [BusinessRuleOut.model_validate(row) for row in rows]


def list_fees(session: Session) -> list[FeeScheduleOut]:
    rows = session.scalars(
        select(FeeSchedule).order_by(FeeSchedule.rail, FeeSchedule.segment)
    ).all()
    return [FeeScheduleOut.model_validate(row) for row in rows]
