"""State-changing payment, exception, approval and reconciliation operations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.audit.actions import SOURCE_API, AuditAction
from app.audit.recorder import record_audit_event
from app.auth.roles import satisfies_role
from app.core import clock
from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.ids import approval_ref, reconciliation_run_ref
from app.domain.exceptions.classification import classify_exception
from app.domain.payments.lifecycle import DEFAULT_EVENT_TYPE_FOR_STATUS, assert_transition
from app.domain.policies.reasons import reason_by_code
from app.domain.reconciliation.compare import (
    CompareResult,
    CreditFact,
    EntryFact,
    compare_batch,
    discrepancy_counts,
    serialize_discrepancies,
)
from app.domain.validation.engine import RuleOutcome, ValidationFacts, evaluate, primary_failure
from app.models.approvals import ApprovalDecision, ApprovalRequest
from app.models.audit import AuditEvent
from app.models.enums import (
    ApprovalDecisionValue,
    ApprovalRiskLevel,
    ApprovalStatus,
    ApprovalSubjectType,
    BatchStatus,
    ExceptionAction,
    ExceptionStatus,
    LedgerDirection,
    LedgerLeg,
    NoteType,
    PaymentEventType,
    PaymentStatus,
    ReconciliationStatus,
    ResolutionCode,
    Role,
    ValidationOutcome,
)
from app.models.exceptions import (
    ExceptionAssignment,
    ExceptionNote,
    ExceptionResolution,
    PaymentException,
)
from app.models.payments import Payment, PaymentEvent, PaymentValidationResult
from app.models.reconciliation import ReconciliationResult
from app.models.settlement import SettlementBatch
from app.models.users import User
from app.schemas.exceptions import (
    AvailableAction,
    ExceptionActionRequest,
    ExceptionApprovalRef,
    TimelineEntry,
)
from app.schemas.payments import AvailableOperation
from app.services.present import ACTION_LABELS, OPEN_EXCEPTION_STATUSES

_TERMINAL_FOR_DUPLICATE = frozenset(
    {PaymentStatus.CANCELLED, PaymentStatus.REJECTED, PaymentStatus.FAILED}
)
_RESOLUTION_FOR_ACTION: dict[ExceptionAction, ResolutionCode] = {
    ExceptionAction.REPAIR_AND_RELEASE: ResolutionCode.REPAIRED_RELEASED,
    ExceptionAction.RELEASE_AS_IS: ResolutionCode.RELEASED_AS_IS,
    ExceptionAction.RETURN_TO_CUSTOMER: ResolutionCode.RETURNED,
    ExceptionAction.CANCEL_PAYMENT: ResolutionCode.CANCELLED,
    ExceptionAction.ESCALATE: ResolutionCode.ESCALATED,
}


def transition(
    session: Session,
    payment: Payment,
    to_status: PaymentStatus,
    *,
    actor: str,
    summary: str,
    event_type: PaymentEventType | None = None,
    detail: dict[str, object] | None = None,
) -> None:
    """Move ``payment`` and append the lifecycle event. Does not commit."""
    assert_transition(payment.status, to_status, payment_ref=payment.payment_ref)
    previous = payment.status
    sequence = session.scalar(
        select(func.max(PaymentEvent.sequence)).where(PaymentEvent.payment_id == payment.id)
    )
    moment = clock.now()
    session.add(
        PaymentEvent(
            payment_id=payment.id,
            sequence=int(sequence or 0) + 1,
            event_type=event_type or DEFAULT_EVENT_TYPE_FOR_STATUS[to_status],
            from_status=previous,
            to_status=to_status,
            occurred_at=moment,
            actor=actor,
            summary=summary,
            detail=dict(detail or {}),
            correlation_id=payment.correlation_id,
        )
    )
    payment.status = to_status
    payment.updated_at = moment
    session.flush()


def _duplicate(session: Session, payment: Payment) -> bool:
    other = session.scalar(
        select(Payment.id).where(
            Payment.customer_id == payment.customer_id,
            Payment.end_to_end_reference == payment.end_to_end_reference,
            Payment.id != payment.id,
            Payment.status.notin_(tuple(_TERMINAL_FOR_DUPLICATE)),
        )
    )
    return other is not None


def facts_for(session: Session, payment: Payment) -> ValidationFacts:
    instruction = payment.instruction
    if instruction is None:
        raise ConflictError(f"Payment {payment.payment_ref} has no instruction to validate")
    return ValidationFacts(
        rail=payment.rail,
        currency=payment.currency,
        amount=payment.amount,
        usd_equivalent=payment.usd_equivalent,
        instructed_name=instruction.instructed_beneficiary_name,
        registered_name=payment.beneficiary.name,
        instructed_identifier=instruction.instructed_identifier,
        registered_identifier=payment.beneficiary.identifier,
        instructed_bic=instruction.instructed_bic,
        account_status=payment.debit_account.status,
        account_currency=payment.debit_account.currency,
        available_balance=payment.debit_account.available_balance,
        fee_amount=payment.fee_amount,
        daily_limit_usd=payment.customer.daily_limit_usd,
        purpose_code=payment.purpose_code,
        end_to_end_reference=payment.end_to_end_reference,
        duplicate_reference=_duplicate(session, payment),
        screening_hit=payment.risk_score >= 90,
        requested_value_date=payment.requested_value_date,
        scenario_date=clock.today(),
    )


def store_validation(session: Session, payment: Payment, outcomes: list[RuleOutcome]) -> None:
    session.execute(
        delete(PaymentValidationResult).where(PaymentValidationResult.payment_id == payment.id)
    )
    moment = clock.now()
    for outcome in outcomes:
        session.add(
            PaymentValidationResult(
                payment_id=payment.id,
                rule_code=outcome.rule_code,
                rule_name=outcome.rule_name,
                outcome=outcome.outcome,
                severity=outcome.severity,
                message=outcome.message,
                evidence=dict(outcome.evidence),
                evaluated_at=moment,
            )
        )
    session.flush()


def needs_approval(payment: Payment, reason_code: str) -> tuple[bool, Role]:
    policy = reason_by_code(reason_code)
    routed = classify_exception(reason_code, payment.usd_equivalent, payment.customer.segment.value)
    role = Role.SUPERVISOR
    if policy is not None and policy.approval_role is not None:
        role = policy.approval_role
    if policy is not None and policy.requires_approval_for_release:
        threshold = policy.approval_amount_threshold_usd
        if threshold is None or payment.usd_equivalent >= threshold:
            return True, role
    if routed.requires_supervisor:
        return True, role
    return False, role


def available_operations(user: User, payment: Payment) -> list[AvailableOperation]:
    analyst = satisfies_role(user.role, Role.ANALYST)
    supervisor = satisfies_role(user.role, Role.SUPERVISOR)
    operations = [
        AvailableOperation(
            action="revalidate",
            label="Re-run validation",
            enabled=analyst and payment.status in {PaymentStatus.CREATED, PaymentStatus.HELD},
            disabled_reason=None
            if analyst and payment.status in {PaymentStatus.CREATED, PaymentStatus.HELD}
            else "Validation can be re-run while a payment is created or held.",
        ),
        AvailableOperation(
            action="cancel",
            label="Cancel payment",
            enabled=supervisor and payment.status in {PaymentStatus.HELD, PaymentStatus.APPROVED},
            disabled_reason=None
            if supervisor and payment.status in {PaymentStatus.HELD, PaymentStatus.APPROVED}
            else "Cancellation requires a supervisor and a held or approved payment.",
        ),
    ]
    return operations


def available_actions(user: User, item: PaymentException) -> list[AvailableAction]:
    policy = reason_by_code(item.reason_code)
    allowed = list(policy.allowed_actions) if policy is not None else list(ExceptionAction)
    open_item = item.status in OPEN_EXCEPTION_STATUSES
    pending = item.status is ExceptionStatus.PENDING_APPROVAL
    actions: list[AvailableAction] = []
    for action in allowed:
        if action is ExceptionAction.ESCALATE:
            actions.append(
                AvailableAction(
                    action=action,
                    label=ACTION_LABELS[action.value],
                    enabled=open_item and not pending and satisfies_role(user.role, Role.ANALYST),
                    requires_approval=False,
                    disabled_reason=None if open_item and not pending else "Not actionable.",
                )
            )
            continue
        required, role = needs_approval(item.payment, item.reason_code)
        direct = (
            satisfies_role(user.role, role) if required else satisfies_role(user.role, Role.ANALYST)
        )
        enabled = open_item and not pending and (direct or satisfies_role(user.role, Role.ANALYST))
        reason = None
        if not open_item or pending:
            reason = "This exception is not waiting on an analyst action."
            enabled = False
        elif action is ExceptionAction.CANCEL_PAYMENT and not satisfies_role(
            user.role, Role.SUPERVISOR
        ):
            enabled = False
            reason = "Cancellation requires a supervisor."
        actions.append(
            AvailableAction(
                action=action,
                label=ACTION_LABELS[action.value],
                enabled=enabled,
                requires_approval=required,
                disabled_reason=reason,
            )
        )
    return actions


def timeline_for(item: PaymentException, audits: list[AuditEvent]) -> list[TimelineEntry]:
    rows: list[TimelineEntry] = []
    for event in item.payment.events:
        rows.append(
            TimelineEntry(
                occurred_at=event.occurred_at,
                kind="PAYMENT_EVENT",
                title=event.summary,
                detail=event.event_type.value,
                actor=event.actor,
            )
        )
    for note in item.notes:
        rows.append(
            TimelineEntry(
                occurred_at=note.created_at,
                kind="NOTE",
                title=note.body,
                detail=note.note_type.value,
                actor=note.author,
            )
        )
    for audit in audits:
        rows.append(
            TimelineEntry(
                occurred_at=audit.occurred_at,
                kind="AUDIT",
                title=audit.summary,
                detail=audit.action,
                actor=audit.actor,
            )
        )
    rows.sort(key=lambda row: row.occurred_at)
    return rows


def _next_numbered(
    session: Session,
    column: InstrumentedAttribute[str],
    prefix: str,
    formatter: Callable[[int], str],
) -> str:
    values = session.scalars(select(column)).all()
    highest = 0
    for value in values:
        if value.startswith(prefix):
            tail = value.removeprefix(prefix).lstrip("-")
            if tail.isdigit():
                highest = max(highest, int(tail))
    return formatter(highest + 1)


def revalidate(session: Session, payment: Payment, user: User) -> None:
    if not satisfies_role(user.role, Role.ANALYST):
        raise ConflictError("Re-validation requires an analyst role")
    if payment.status not in {PaymentStatus.CREATED, PaymentStatus.HELD}:
        raise ConflictError(f"Cannot re-validate a payment in status {payment.status.value}")
    if payment.status is PaymentStatus.CREATED:
        transition(
            session,
            payment,
            PaymentStatus.VALIDATING,
            actor=user.username,
            summary="Validation started",
        )
    elif payment.status is PaymentStatus.HELD:
        transition(
            session,
            payment,
            PaymentStatus.VALIDATING,
            actor=user.username,
            summary="Validation restarted after repair",
            event_type=PaymentEventType.VALIDATION_STARTED,
        )
    outcomes = evaluate(facts_for(session, payment))
    store_validation(session, payment, outcomes)
    failure = primary_failure(outcomes)
    if failure is None:
        transition(
            session,
            payment,
            PaymentStatus.APPROVED,
            actor=user.username,
            summary="Validation passed",
            event_type=PaymentEventType.VALIDATION_PASSED,
        )
        _resolve_open(session, payment, user, ResolutionCode.REPAIRED_RELEASED, "Validation passed")
    else:
        transition(
            session,
            payment,
            PaymentStatus.HELD,
            actor=user.username,
            summary=failure.message,
            event_type=PaymentEventType.VALIDATION_FAILED,
        )
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.PAYMENT_VALIDATED,
        entity_type="PAYMENT",
        entity_ref=payment.payment_ref,
        summary="Payment validation re-run",
        correlation_id=payment.correlation_id,
    )


def cancel_payment(session: Session, payment: Payment, user: User, reason: str | None) -> None:
    if not satisfies_role(user.role, Role.SUPERVISOR):
        raise ConflictError("Cancellation requires a supervisor")
    if payment.status not in {PaymentStatus.HELD, PaymentStatus.APPROVED}:
        raise ConflictError(f"Cannot cancel a payment in status {payment.status.value}")
    summary = reason.strip() if reason else "Cancelled by operations"
    transition(
        session,
        payment,
        PaymentStatus.CANCELLED,
        actor=user.username,
        summary=summary,
    )
    payment.failure_reason = summary[:280]
    _resolve_open(session, payment, user, ResolutionCode.CANCELLED, summary)
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.PAYMENT_CANCELLED,
        entity_type="PAYMENT",
        entity_ref=payment.payment_ref,
        summary=summary,
        correlation_id=payment.correlation_id,
    )


def _resolve_open(
    session: Session,
    payment: Payment,
    user: User,
    code: ResolutionCode,
    summary: str,
) -> None:
    for item in payment.exceptions:
        if item.status in OPEN_EXCEPTION_STATUSES:
            item.status = ExceptionStatus.RESOLVED
            item.resolved_at = clock.now()
            item.resolution_code = code
            session.add(
                ExceptionResolution(
                    exception_id=item.id,
                    action=ExceptionAction.CANCEL_PAYMENT
                    if code is ResolutionCode.CANCELLED
                    else ExceptionAction.RELEASE_AS_IS,
                    resolution_code=code,
                    performed_by=user.username,
                    performed_at=clock.now(),
                    details={"summary": summary},
                )
            )
    session.flush()


def assign_exception(
    session: Session, item: PaymentException, user: User, assignee: User, note: str | None
) -> None:
    if not satisfies_role(user.role, Role.ANALYST):
        raise ConflictError("Assignment requires an analyst role")
    if item.status not in OPEN_EXCEPTION_STATUSES:
        raise ConflictError("A resolved exception cannot be assigned")
    item.assigned_to_user_id = assignee.id
    if item.status is ExceptionStatus.OPEN:
        item.status = ExceptionStatus.IN_REVIEW
    session.add(
        ExceptionAssignment(
            exception_id=item.id,
            assigned_to_user_id=assignee.id,
            assigned_by=user.username,
            assigned_at=clock.now(),
            note=note,
        )
    )
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.EXCEPTION_ASSIGNED,
        entity_type="EXCEPTION",
        entity_ref=item.exception_ref,
        summary=f"Assigned to {assignee.display_name}",
        correlation_id=item.correlation_id,
    )


def add_note(
    session: Session, item: PaymentException, user: User, body: str, note_type: NoteType
) -> None:
    if not satisfies_role(user.role, Role.ANALYST) and user.role is not Role.READONLY:
        raise ConflictError("Notes require an analyst role")
    if user.role is Role.READONLY:
        raise ConflictError("Read-only identities cannot add notes")
    session.add(
        ExceptionNote(
            exception_id=item.id,
            author=user.username,
            note_type=note_type,
            body=body,
            created_at=clock.now(),
        )
    )
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.EXCEPTION_NOTE_ADDED,
        entity_type="EXCEPTION",
        entity_ref=item.exception_ref,
        summary=body[:180],
        correlation_id=item.correlation_id,
    )


def perform_action(
    session: Session, item: PaymentException, user: User, request: ExceptionActionRequest
) -> str | None:
    """Apply an exception action. Returns an approval reference when one was raised."""
    if (
        item.status not in OPEN_EXCEPTION_STATUSES
        or item.status is ExceptionStatus.PENDING_APPROVAL
    ):
        raise ConflictError("This exception is not waiting on an analyst action")
    policy = reason_by_code(item.reason_code)
    if policy is not None and request.action not in policy.allowed_actions:
        raise ValidationFailed(f"{request.action.value} is not allowed for {item.reason_code}")
    if request.action is ExceptionAction.ESCALATE:
        item.status = ExceptionStatus.ESCALATED
        record_audit_event(
            session,
            actor=user.username,
            actor_role=user.role,
            action=AuditAction.EXCEPTION_ESCALATED,
            entity_type="EXCEPTION",
            entity_ref=item.exception_ref,
            summary=request.justification,
            correlation_id=item.correlation_id,
        )
        return None
    if request.action is ExceptionAction.CANCEL_PAYMENT and not satisfies_role(
        user.role, Role.SUPERVISOR
    ):
        raise ConflictError("Cancellation requires a supervisor")
    required, role = needs_approval(item.payment, item.reason_code)
    if required and not satisfies_role(user.role, role):
        return _raise_approval(session, item, user, request, role)
    _apply_action(session, item, user, request, approval=None)
    return None


def _raise_approval(
    session: Session,
    item: PaymentException,
    user: User,
    request: ExceptionActionRequest,
    role: Role,
) -> str:
    reference = _next_numbered(session, ApprovalRequest.approval_ref, "MGB-APR-", approval_ref)
    moment = clock.now()
    amount = item.payment.usd_equivalent
    risk = ApprovalRiskLevel.HIGH if amount >= Decimal("100000") else ApprovalRiskLevel.MEDIUM
    if item.severity.value == "CRITICAL":
        risk = ApprovalRiskLevel.CRITICAL
    approval = ApprovalRequest(
        approval_ref=reference,
        subject_type=ApprovalSubjectType.PAYMENT_EXCEPTION,
        subject_ref=item.exception_ref,
        payment_ref=item.payment.payment_ref,
        requested_action=request.action.value,
        summary=f"{ACTION_LABELS[request.action.value]} for {item.payment.payment_ref}",
        justification=request.justification,
        risk_level=risk,
        amount=item.payment.amount,
        currency=item.payment.currency,
        requested_by=user.username,
        required_role=role,
        status=ApprovalStatus.PENDING,
        created_at=moment,
        expires_at=moment + timedelta(hours=8),
    )
    session.add(approval)
    session.flush()
    session.add(
        ExceptionResolution(
            exception_id=item.id,
            action=request.action,
            resolution_code=None,
            performed_by=user.username,
            approval_request_id=approval.id,
            performed_at=moment,
            details={
                "justification": request.justification,
                "repaired_beneficiary_name": request.repaired_beneficiary_name,
            },
        )
    )
    item.status = ExceptionStatus.PENDING_APPROVAL
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.APPROVAL_REQUESTED,
        entity_type="APPROVAL",
        entity_ref=reference,
        summary=approval.summary,
        correlation_id=item.correlation_id,
        metadata={"exception_ref": item.exception_ref},
    )
    return reference


def _apply_action(
    session: Session,
    item: PaymentException,
    user: User,
    request: ExceptionActionRequest,
    approval: ApprovalRequest | None,
) -> None:
    payment = item.payment
    if request.action is ExceptionAction.REPAIR_AND_RELEASE:
        instruction = payment.instruction
        if instruction is None or not request.repaired_beneficiary_name:
            raise ValidationFailed("A repaired beneficiary name is required")
        instruction.instructed_beneficiary_name = request.repaired_beneficiary_name
        outcomes = evaluate(facts_for(session, payment))
        store_validation(session, payment, outcomes)
        failure = primary_failure(outcomes)
        if failure is not None:
            raise ValidationFailed(failure.message)
        if payment.status is PaymentStatus.HELD:
            transition(
                session,
                payment,
                PaymentStatus.APPROVED,
                actor=user.username,
                summary="Released after beneficiary repair",
                event_type=PaymentEventType.REPAIRED,
            )
    elif request.action is ExceptionAction.RELEASE_AS_IS:
        if payment.status is PaymentStatus.HELD:
            transition(
                session,
                payment,
                PaymentStatus.APPROVED,
                actor=user.username,
                summary="Released without changing the instruction",
                event_type=PaymentEventType.RELEASED,
            )
    elif request.action is ExceptionAction.RETURN_TO_CUSTOMER:
        if payment.status is PaymentStatus.HELD:
            transition(
                session,
                payment,
                PaymentStatus.REJECTED,
                actor=user.username,
                summary=request.justification,
            )
        payment.failure_reason = request.justification[:280]
    elif request.action is ExceptionAction.CANCEL_PAYMENT:
        if payment.status in {PaymentStatus.HELD, PaymentStatus.APPROVED}:
            transition(
                session,
                payment,
                PaymentStatus.CANCELLED,
                actor=user.username,
                summary=request.justification,
            )
        payment.failure_reason = request.justification[:280]
    code = _RESOLUTION_FOR_ACTION[request.action]
    item.status = ExceptionStatus.RESOLVED
    item.resolved_at = clock.now()
    item.resolution_code = code
    session.add(
        ExceptionResolution(
            exception_id=item.id,
            action=request.action,
            resolution_code=code,
            performed_by=user.username,
            approval_request_id=approval.id if approval is not None else None,
            performed_at=clock.now(),
            details={"justification": request.justification},
        )
    )
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.EXCEPTION_RESOLVED,
        entity_type="EXCEPTION",
        entity_ref=item.exception_ref,
        summary=request.justification,
        correlation_id=item.correlation_id,
        source_service=SOURCE_API,
    )


def decide_approval(
    session: Session,
    approval: ApprovalRequest,
    user: User,
    decision: ApprovalDecisionValue,
    rationale: str,
) -> None:
    if approval.requested_by == user.username:
        raise ConflictError("The requestor cannot decide their own approval")
    if not satisfies_role(user.role, approval.required_role) or user.role is Role.ENGINEER:
        raise ConflictError("This role cannot decide the approval")
    if approval.status is not ApprovalStatus.PENDING:
        raise ConflictError("This approval is no longer pending")
    if approval.expires_at <= clock.now():
        approval.status = ApprovalStatus.EXPIRED
        raise ConflictError("This approval has expired")
    moment = clock.now()
    session.add(
        ApprovalDecision(
            approval_request_id=approval.id,
            decided_by=user.username,
            decision=decision,
            rationale=rationale,
            decided_at=moment,
        )
    )
    approval.decided_at = moment
    approval.status = (
        ApprovalStatus.APPROVED
        if decision is ApprovalDecisionValue.APPROVED
        else ApprovalStatus.REJECTED
    )
    item = session.scalar(
        select(PaymentException).where(PaymentException.exception_ref == approval.subject_ref)
    )
    if item is not None and decision is ApprovalDecisionValue.APPROVED:
        pending = next(
            (row for row in item.resolutions if row.approval_request_id == approval.id),
            None,
        )
        repaired = None
        if pending is not None:
            raw = pending.details.get("repaired_beneficiary_name")
            repaired = raw if isinstance(raw, str) else None
        action_request = ExceptionActionRequest(
            action=ExceptionAction(approval.requested_action),
            repaired_beneficiary_name=repaired,
            justification=rationale,
        )
        _apply_action(session, item, user, action_request, approval)
    elif item is not None:
        item.status = ExceptionStatus.IN_REVIEW
        item.resolution_code = ResolutionCode.REJECTED_BY_APPROVER
    record_audit_event(
        session,
        actor=user.username,
        actor_role=user.role,
        action=AuditAction.APPROVAL_DECIDED,
        entity_type="APPROVAL",
        entity_ref=approval.approval_ref,
        summary=f"{decision.value}: {rationale}",
        correlation_id=item.correlation_id if item is not None else approval.approval_ref,
    )


def reconcile(
    session: Session, batch: SettlementBatch, *, actor: str, notes: str | None
) -> ReconciliationResult:
    if batch.status not in {BatchStatus.SETTLED, BatchStatus.DISCREPANCY, BatchStatus.RECONCILED}:
        raise ConflictError(
            f"Batch {batch.batch_ref} is {batch.status.value} and cannot be reconciled"
        )
    result = compare_batch(_entry_facts(batch), _credit_facts(batch))
    existing = session.scalar(
        select(ReconciliationResult)
        .where(
            ReconciliationResult.batch_id == batch.id,
            ReconciliationResult.input_hash == result.input_hash,
        )
        .order_by(ReconciliationResult.id.desc())
        .limit(1)
    )
    if existing is not None:
        return existing
    reference = _next_numbered(session, ReconciliationResult.run_ref, "RR-", reconciliation_run_ref)
    row = ReconciliationResult(
        run_ref=reference,
        batch_id=batch.id,
        run_at=clock.now(),
        status=result.status,
        matched_count=result.matched_count,
        unmatched_count=result.unmatched_count,
        expected_total=result.expected_total,
        recorded_total=result.recorded_total,
        variance=result.variance,
        unmatched_refs=result.unmatched_refs,
        discrepancies=serialize_discrepancies(result.discrepancies),
        input_hash=result.input_hash,
        notes=notes,
    )
    session.add(row)
    batch.recorded_total = result.recorded_total
    if result.status is ReconciliationStatus.MATCHED:
        batch.status = BatchStatus.RECONCILED
        batch.reconciled_at = clock.now()
    elif result.unmatched_count:
        batch.status = BatchStatus.DISCREPANCY
    record_audit_event(
        session,
        actor=actor,
        action=AuditAction.RECONCILIATION_RUN,
        entity_type="RECONCILIATION",
        entity_ref=batch.batch_ref,
        summary=(
            f"{result.status.value}: variance {result.variance} "
            f"({result.unmatched_count} unmatched)"
        ),
        correlation_id=batch.correlation_id,
        metadata={
            "run_ref": reference,
            "input_hash": result.input_hash,
            "discrepancy_counts": discrepancy_counts(result.discrepancies),
        },
    )
    session.flush()
    return row


def _entry_facts(batch: SettlementBatch) -> list[EntryFact]:
    return [
        EntryFact(
            entry_ref=entry.entry_ref,
            payment_ref=entry.payment.payment_ref if entry.payment is not None else None,
            amount=entry.amount,
        )
        for entry in batch.entries
    ]


def _credit_facts(batch: SettlementBatch) -> list[CreditFact]:
    return [
        CreditFact(
            entry_ref=ledger.entry_ref,
            payment_ref=ledger.payment.payment_ref if ledger.payment is not None else None,
            amount=ledger.amount,
        )
        for ledger in batch.ledger_entries
        if ledger.leg is LedgerLeg.PRINCIPAL and ledger.direction is LedgerDirection.CREDIT
    ]


def compare_existing(batch: SettlementBatch) -> CompareResult:
    return compare_batch(_entry_facts(batch), _credit_facts(batch))


def require_payment(session: Session, payment_ref: str) -> Payment:
    payment = session.scalar(select(Payment).where(Payment.payment_ref == payment_ref))
    if payment is None:
        raise NotFoundError.for_entity("payment", payment_ref)
    return payment


def require_exception(session: Session, exception_ref: str) -> PaymentException:
    item = session.scalar(
        select(PaymentException).where(PaymentException.exception_ref == exception_ref)
    )
    if item is None:
        raise NotFoundError.for_entity("exception", exception_ref)
    return item


def approval_link(item: PaymentException) -> ExceptionApprovalRef | None:
    for resolution in reversed(item.resolutions):
        approval = resolution.approval_request
        if approval is not None and approval.status is ApprovalStatus.PENDING:
            return ExceptionApprovalRef(
                approval_ref=approval.approval_ref,
                status=approval.status,
                required_role=approval.required_role,
                requested_by=approval.requested_by,
            )
    return None


def count_failures(payment: Payment) -> int:
    return sum(1 for row in payment.validation_results if row.outcome is ValidationOutcome.FAIL)
