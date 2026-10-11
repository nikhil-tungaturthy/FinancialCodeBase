"""Map persisted rows onto the API contract."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core import clock
from app.models.approvals import ApprovalRequest
from app.models.audit import AuditEvent
from app.models.enums import (
    ExceptionStatus,
    FeeSource,
    PaymentStatus,
    Rail,
    ReconciliationStatus,
    Role,
)
from app.models.exceptions import PaymentException
from app.models.ledger import LedgerEntry
from app.models.payments import Payment, PaymentEvent, PaymentInstruction, PaymentValidationResult
from app.models.reconciliation import ReconciliationResult
from app.models.settlement import SettlementBatch, SettlementEntry
from app.models.users import User
from app.schemas.approvals import ApprovalDecisionOut, ApprovalSummary, CanDecide
from app.schemas.audit import AuditEventOut
from app.schemas.common import UserRef
from app.schemas.exceptions import (
    AvailableAction,
    ExceptionApprovalRef,
    ExceptionAssignmentOut,
    ExceptionDetail,
    ExceptionInstructionSnippet,
    ExceptionNoteOut,
    ExceptionPaymentContext,
    ExceptionQueueItem,
    ExceptionRecord,
    ExceptionResolutionOut,
    TimelineEntry,
)
from app.schemas.ledger import LedgerEntryOut
from app.schemas.payments import (
    AvailableOperation,
    FeeOut,
    PaymentAccountRef,
    PaymentBeneficiaryRef,
    PaymentCustomerRef,
    PaymentDetail,
    PaymentEventOut,
    PaymentExceptionRef,
    PaymentInstructionOut,
    PaymentRecord,
    PaymentSettlementOut,
    PaymentSummary,
    ValidationResultOut,
)
from app.schemas.settlement import (
    BatchDetail,
    BatchSummary,
    ReconciliationResultOut,
    SettlementEntryOut,
)

OPEN_EXCEPTION_STATUSES = frozenset(
    {
        ExceptionStatus.OPEN,
        ExceptionStatus.IN_REVIEW,
        ExceptionStatus.PENDING_APPROVAL,
        ExceptionStatus.ESCALATED,
    }
)

ACTION_LABELS: dict[str, str] = {
    "REPAIR_AND_RELEASE": "Repair and release",
    "RELEASE_AS_IS": "Release as instructed",
    "RETURN_TO_CUSTOMER": "Return to customer",
    "CANCEL_PAYMENT": "Cancel payment",
    "ESCALATE": "Escalate",
}


def minutes_between(later: datetime, earlier: datetime) -> int:
    return int((later - earlier).total_seconds() // 60)


def user_ref(user: User | None) -> UserRef | None:
    if user is None:
        return None
    return UserRef(username=user.username, display_name=user.display_name)


def audit_out(event: AuditEvent) -> AuditEventOut:
    return AuditEventOut.model_validate(event)


def open_exception(payment: Payment) -> PaymentException | None:
    for item in payment.exceptions:
        if item.status in OPEN_EXCEPTION_STATUSES:
            return item
    return payment.exceptions[-1] if payment.exceptions else None


def payment_summary(payment: Payment, exception: PaymentException | None = None) -> PaymentSummary:
    current = exception if exception is not None else open_exception(payment)
    visible = current if current is not None and current.status in OPEN_EXCEPTION_STATUSES else None
    return PaymentSummary(
        payment_ref=payment.payment_ref,
        customer_name=payment.customer.legal_name,
        beneficiary_name=payment.beneficiary.name,
        rail=payment.rail,
        currency=payment.currency,
        amount=payment.amount,
        usd_equivalent=payment.usd_equivalent,
        created_at=payment.created_at,
        status=payment.status,
        priority=payment.priority,
        risk_tier=payment.risk_tier,
        settlement_window_key=payment.settlement_window_key,
        settlement_cutoff_at=payment.settlement_cutoff_at,
        has_open_exception=visible is not None,
        exception_ref=visible.exception_ref if visible is not None else None,
    )


def _cutoff_local(payment: Payment) -> str | None:
    if payment.settlement_cutoff_at is None or not payment.settlement_timezone:
        return None
    local = payment.settlement_cutoff_at.astimezone(ZoneInfo(payment.settlement_timezone))
    return f"{local:%H:%M}"


def fee_source_for(rail: Rail) -> FeeSource:
    if rail in {Rail.WIRE_USD, Rail.SWIFT_INTL}:
        return FeeSource.LEGACY_FEECALC01
    return FeeSource.MODERN


def payment_detail(
    payment: Payment,
    audit_events: list[AuditEvent],
    operations: list[AvailableOperation],
) -> PaymentDetail:
    exception = open_exception(payment)
    batch = payment.settlement_batch
    instruction = payment.instruction
    now = clock.now()
    minutes = (
        minutes_between(payment.settlement_cutoff_at, now)
        if payment.settlement_cutoff_at is not None
        else None
    )
    return PaymentDetail(
        payment=PaymentRecord(
            payment_ref=payment.payment_ref,
            channel=payment.channel,
            rail=payment.rail,
            currency=payment.currency,
            amount=payment.amount,
            fee_amount=payment.fee_amount,
            fee_currency=payment.fee_currency,
            usd_equivalent=payment.usd_equivalent,
            status=payment.status,
            priority=payment.priority,
            risk_score=payment.risk_score,
            risk_tier=payment.risk_tier,
            purpose_code=payment.purpose_code,
            end_to_end_reference=payment.end_to_end_reference,
            remittance_info=payment.remittance_info,
            requested_value_date=payment.requested_value_date,
            value_date=payment.value_date,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            settlement_window_key=payment.settlement_window_key,
            settlement_cutoff_at=payment.settlement_cutoff_at,
            settlement_timezone=payment.settlement_timezone,
            correlation_id=payment.correlation_id,
            idempotency_key=payment.idempotency_key,
            failure_reason=payment.failure_reason,
        ),
        customer=PaymentCustomerRef(
            ref=payment.customer.customer_ref,
            name=payment.customer.legal_name,
            segment=payment.customer.segment,
            country=payment.customer.country,
        ),
        debit_account=PaymentAccountRef(
            ref=payment.debit_account.account_ref,
            masked_identifier=payment.debit_account.masked_identifier,
            currency=payment.debit_account.currency,
            account_type=payment.debit_account.account_type,
        ),
        beneficiary=PaymentBeneficiaryRef(
            ref=payment.beneficiary.beneficiary_ref,
            name=payment.beneficiary.name,
            masked_identifier=payment.beneficiary.masked_identifier,
            bic=payment.beneficiary.bic,
            bank_name=payment.beneficiary.bank_name,
            country=payment.beneficiary.country,
            verification_status=payment.beneficiary.verification_status,
        ),
        instruction=_instruction_out(instruction) if instruction is not None else None,
        fee=FeeOut(
            amount=payment.fee_amount,
            currency=payment.fee_currency,
            source=fee_source_for(payment.rail),
        ),
        settlement=PaymentSettlementOut(
            window_key=payment.settlement_window_key,
            cutoff_at=payment.settlement_cutoff_at,
            timezone=payment.settlement_timezone,
            cutoff_local_label=_cutoff_local(payment),
            value_date=payment.value_date,
            batch_ref=batch.batch_ref if batch is not None else None,
            batch_status=batch.status.value if batch is not None else None,
            minutes_to_cutoff=minutes,
        ),
        validation_results=[_validation_out(row) for row in payment.validation_results],
        events=[_event_out(row) for row in payment.events],
        exception=(
            PaymentExceptionRef(
                exception_ref=exception.exception_ref,
                reason_code=exception.reason_code,
                reason_title=exception.reason_title,
                severity=exception.severity,
                status=exception.status,
            )
            if exception is not None
            else None
        ),
        audit_events=[audit_out(row) for row in audit_events],
        available_operations=operations,
    )


def _instruction_out(instruction: PaymentInstruction) -> PaymentInstructionOut:
    return PaymentInstructionOut(
        channel=instruction.channel,
        instructed_beneficiary_name=instruction.instructed_beneficiary_name,
        instructed_identifier=instruction.instructed_identifier,
        instructed_bic=instruction.instructed_bic,
        instructed_bank_name=instruction.instructed_bank_name,
        instructed_country=instruction.instructed_country,
        remittance_info=instruction.remittance_info,
        received_at=instruction.received_at,
        submitted_by=instruction.submitted_by,
        raw_payload_hash=instruction.raw_payload_hash,
    )


def _validation_out(row: PaymentValidationResult) -> ValidationResultOut:
    return ValidationResultOut.model_validate(row)


def _event_out(row: PaymentEvent) -> PaymentEventOut:
    return PaymentEventOut.model_validate(row)


def exception_queue_item(item: PaymentException) -> ExceptionQueueItem:
    payment = item.payment
    now = clock.now()
    return ExceptionQueueItem(
        exception_ref=item.exception_ref,
        payment_ref=payment.payment_ref,
        reason_code=item.reason_code,
        reason_title=item.reason_title,
        severity=item.severity,
        status=item.status,
        amount=payment.amount,
        currency=payment.currency.value,
        usd_equivalent=payment.usd_equivalent,
        customer_name=payment.customer.legal_name,
        opened_at=item.opened_at,
        due_by=item.due_by,
        age_minutes=max(0, minutes_between(now, item.opened_at)),
        minutes_to_due=minutes_between(item.due_by, now) if item.due_by is not None else None,
        assigned_to=user_ref(item.assigned_to),
        queue=item.queue,
        priority=payment.priority,
    )


def exception_record(item: PaymentException) -> ExceptionRecord:
    return ExceptionRecord(
        exception_ref=item.exception_ref,
        payment_ref=item.payment.payment_ref,
        reason_code=item.reason_code,
        reason_title=item.reason_title,
        severity=item.severity,
        status=item.status,
        opened_at=item.opened_at,
        due_by=item.due_by,
        assigned_to=user_ref(item.assigned_to),
        queue=item.queue,
        summary=item.summary,
        resolved_at=item.resolved_at,
        resolution_code=item.resolution_code,
        correlation_id=item.correlation_id,
    )


def _mask_identifier(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) <= 4:
        return "****"
    return f"****{trimmed[-4:]}"


def exception_payment_context(payment: Payment) -> ExceptionPaymentContext:
    summary = payment_summary(payment)
    instruction = payment.instruction
    snippet = None
    if instruction is not None:
        snippet = ExceptionInstructionSnippet(
            instructed_beneficiary_name=instruction.instructed_beneficiary_name,
            instructed_identifier_masked=_mask_identifier(instruction.instructed_identifier),
            instructed_bic=instruction.instructed_bic,
            instructed_bank_name=instruction.instructed_bank_name,
            remittance_info=instruction.remittance_info,
            submitted_by=instruction.submitted_by,
            received_at=instruction.received_at,
        )
    beneficiary = PaymentBeneficiaryRef(
        ref=payment.beneficiary.beneficiary_ref,
        name=payment.beneficiary.name,
        masked_identifier=payment.beneficiary.masked_identifier,
        bic=payment.beneficiary.bic,
        bank_name=payment.beneficiary.bank_name,
        country=payment.beneficiary.country,
        verification_status=payment.beneficiary.verification_status,
    )
    return ExceptionPaymentContext(
        **summary.model_dump(),
        beneficiary=beneficiary,
        instruction=snippet,
    )


def batch_summary(batch: SettlementBatch) -> BatchSummary:
    latest = batch.reconciliation_results[-1] if batch.reconciliation_results else None
    variance: Decimal | None = None
    if batch.recorded_total is not None:
        variance = batch.recorded_total - batch.expected_total
    return BatchSummary(
        batch_ref=batch.batch_ref,
        rail=batch.rail,
        currency=batch.currency,
        value_date=batch.value_date,
        window_key=batch.window_key,
        timezone=batch.timezone,
        cutoff_at=batch.cutoff_at,
        status=batch.status,
        expected_total=batch.expected_total,
        recorded_total=batch.recorded_total,
        variance=variance,
        entry_count=batch.entry_count,
        matched_count=latest.matched_count if latest is not None else None,
        unmatched_count=latest.unmatched_count if latest is not None else None,
        reconciliation_status=latest.status if latest is not None else ReconciliationStatus.NOT_RUN,
        settled_at=batch.settled_at,
    )


def reconciliation_out(
    result: ReconciliationResult, batch: SettlementBatch
) -> ReconciliationResultOut:
    return ReconciliationResultOut(
        run_ref=result.run_ref,
        batch_ref=batch.batch_ref,
        run_at=result.run_at,
        status=result.status,
        matched_count=result.matched_count,
        unmatched_count=result.unmatched_count,
        expected_total=result.expected_total,
        recorded_total=result.recorded_total,
        variance=result.variance,
        currency=batch.currency,
        unmatched_refs=list(result.unmatched_refs),
        input_hash=result.input_hash,
        notes=result.notes,
    )


def ledger_out(entry: LedgerEntry) -> LedgerEntryOut:
    return LedgerEntryOut(
        entry_ref=entry.entry_ref,
        journal_ref=entry.journal_ref,
        payment_ref=entry.payment.payment_ref if entry.payment is not None else None,
        batch_ref=entry.batch.batch_ref if entry.batch is not None else None,
        account_code=entry.account_code,
        direction=entry.direction,
        amount=entry.amount,
        currency=entry.currency,
        posted_at=entry.posted_at,
        value_date=entry.value_date,
        description=entry.description,
        posting_source=entry.posting_source,
        leg=entry.leg,
        correlation_id=entry.correlation_id,
    )


def settlement_entry_out(entry: SettlementEntry, matched: bool | None) -> SettlementEntryOut:
    return SettlementEntryOut(
        entry_ref=entry.entry_ref,
        payment_ref=entry.payment.payment_ref if entry.payment is not None else None,
        amount=entry.amount,
        currency=entry.currency,
        status=entry.status,
        external_reference=entry.external_reference,
        settled_at=entry.settled_at,
        matched=matched,
        sequence=entry.sequence,
    )


def batch_detail(batch: SettlementBatch) -> BatchDetail:
    latest = batch.reconciliation_results[-1] if batch.reconciliation_results else None
    unmatched = set(latest.unmatched_refs) if latest is not None else set()
    payments_with_unmatched_credit = {
        ledger.payment_id
        for ledger in batch.ledger_entries
        if ledger.entry_ref in unmatched and ledger.payment_id is not None
    }
    entries: list[SettlementEntryOut] = []
    for entry in batch.entries:
        if latest is None:
            flag: bool | None = None
        elif entry.entry_ref in unmatched or entry.payment_id in payments_with_unmatched_credit:
            flag = False
        else:
            flag = True
        entries.append(settlement_entry_out(entry, flag))
    return BatchDetail(
        batch=batch_summary(batch),
        entries=entries,
        ledger_entries=[ledger_out(row) for row in batch.ledger_entries],
        reconciliation=reconciliation_out(latest, batch) if latest is not None else None,
        reconciliation_history=[
            reconciliation_out(row, batch) for row in batch.reconciliation_results
        ],
    )


def approval_is_expired(request: ApprovalRequest, now: datetime | None = None) -> bool:
    moment = now or clock.now()
    return request.status.value == "PENDING" and request.expires_at <= moment


def approval_summary(request: ApprovalRequest, requester: User) -> ApprovalSummary:
    decision = request.decisions[-1] if request.decisions else None
    return ApprovalSummary(
        approval_ref=request.approval_ref,
        subject_type=request.subject_type,
        subject_ref=request.subject_ref,
        payment_ref=request.payment_ref,
        requested_action=request.requested_action,
        summary=request.summary,
        risk_level=request.risk_level,
        amount=request.amount,
        currency=request.currency,
        requested_by=UserRef(username=requester.username, display_name=requester.display_name),
        required_role=request.required_role,
        status=request.status,
        is_expired=approval_is_expired(request),
        created_at=request.created_at,
        expires_at=request.expires_at,
        decided_at=request.decided_at,
        decision=(
            ApprovalDecisionOut(
                decided_by=decision.decided_by,
                decision=decision.decision,
                rationale=decision.rationale,
                decided_at=decision.decided_at,
            )
            if decision is not None
            else None
        ),
    )


def can_decide(request: ApprovalRequest, user: User, requester_username: str) -> CanDecide:
    if request.status.value != "PENDING":
        return CanDecide(allowed=False, reason="This request is no longer pending.")
    if approval_is_expired(request):
        return CanDecide(allowed=False, reason="This request has expired.")
    if user.username == requester_username:
        return CanDecide(allowed=False, reason="The requestor cannot approve their own request.")
    from app.auth.roles import satisfies_role

    if not satisfies_role(user.role, request.required_role):
        needed = request.required_role.value.replace("_", " ").title()
        return CanDecide(allowed=False, reason=f"Requires the {needed} role.")
    if user.role is Role.ENGINEER:
        return CanDecide(allowed=False, reason="Engineering roles cannot decide approvals.")
    return CanDecide(allowed=True, reason=None)


def cancellable(status: PaymentStatus) -> bool:
    return status in {PaymentStatus.HELD, PaymentStatus.APPROVED}


def exception_detail(
    item: PaymentException,
    timeline: list[TimelineEntry],
    actions: list[AvailableAction],
    approval: ExceptionApprovalRef | None,
) -> ExceptionDetail:
    return ExceptionDetail(
        exception=exception_record(item),
        payment=exception_payment_context(item.payment),
        validation_results=[_validation_out(row) for row in item.payment.validation_results],
        notes=[
            ExceptionNoteOut(
                id=note.id,
                author=note.author,
                note_type=note.note_type,
                body=note.body,
                created_at=note.created_at,
            )
            for note in item.notes
        ],
        assignments=[
            ExceptionAssignmentOut(
                assigned_to=UserRef(
                    username=row.assigned_to.username,
                    display_name=row.assigned_to.display_name,
                ),
                assigned_by=row.assigned_by,
                assigned_at=row.assigned_at,
                note=row.note,
            )
            for row in item.assignments
        ],
        resolutions=[
            ExceptionResolutionOut(
                action=row.action,
                resolution_code=row.resolution_code,
                performed_by=row.performed_by,
                approval_ref=(
                    row.approval_request.approval_ref if row.approval_request is not None else None
                ),
                performed_at=row.performed_at,
                details=row.details,
            )
            for row in item.resolutions
        ],
        timeline=timeline,
        approval_request=approval,
        available_actions=actions,
    )
