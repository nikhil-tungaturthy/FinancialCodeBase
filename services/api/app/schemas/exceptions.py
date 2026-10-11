"""Exception queue / workbench contract and action request bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models.enums import (
    ApprovalStatus,
    ExceptionAction,
    ExceptionSeverity,
    ExceptionStatus,
    NoteType,
    PaymentPriority,
    ResolutionCode,
    Role,
)
from app.schemas.common import ApiModel, JSONDict, Money, RequestModel, UserRef
from app.schemas.payments import PaymentBeneficiaryRef, PaymentSummary, ValidationResultOut

ExceptionSortField = Literal["opened_at", "due_by", "severity", "amount", "status", "exception_ref"]
TimelineKind = Literal["PAYMENT_EVENT", "AUDIT", "NOTE"]


class ExceptionQueueItem(ApiModel):
    exception_ref: str
    payment_ref: str
    reason_code: str
    reason_title: str
    severity: ExceptionSeverity
    status: ExceptionStatus
    amount: Money
    currency: str
    usd_equivalent: Money
    customer_name: str
    opened_at: datetime
    due_by: datetime | None = None
    age_minutes: int
    minutes_to_due: int | None = None
    assigned_to: UserRef | None = None
    queue: str
    priority: PaymentPriority


class ExceptionRecord(ApiModel):
    exception_ref: str
    payment_ref: str
    reason_code: str
    reason_title: str
    severity: ExceptionSeverity
    status: ExceptionStatus
    opened_at: datetime
    due_by: datetime | None = None
    assigned_to: UserRef | None = None
    queue: str
    summary: str
    resolved_at: datetime | None = None
    resolution_code: ResolutionCode | None = None
    correlation_id: str


class ExceptionInstructionSnippet(ApiModel):
    instructed_beneficiary_name: str
    instructed_identifier_masked: str
    instructed_bic: str | None = None
    instructed_bank_name: str | None = None
    remittance_info: str | None = None
    submitted_by: str
    received_at: datetime


class ExceptionPaymentContext(PaymentSummary):
    """The related payment: summary fields plus beneficiary and instruction snippet."""

    beneficiary: PaymentBeneficiaryRef
    instruction: ExceptionInstructionSnippet | None = None


class ExceptionNoteOut(ApiModel):
    id: int
    author: str
    note_type: NoteType
    body: str
    created_at: datetime


class ExceptionAssignmentOut(ApiModel):
    assigned_to: UserRef
    assigned_by: str
    assigned_at: datetime
    note: str | None = None


class ExceptionResolutionOut(ApiModel):
    action: ExceptionAction
    resolution_code: ResolutionCode | None = None
    performed_by: str
    approval_ref: str | None = None
    performed_at: datetime
    details: JSONDict = {}


class TimelineEntry(ApiModel):
    occurred_at: datetime
    kind: TimelineKind
    title: str
    detail: str | None = None
    actor: str


class ExceptionApprovalRef(ApiModel):
    approval_ref: str
    status: ApprovalStatus
    required_role: Role
    requested_by: str


class AvailableAction(ApiModel):
    action: ExceptionAction
    label: str
    enabled: bool
    requires_approval: bool = False
    disabled_reason: str | None = None


class ExceptionDetail(ApiModel):
    exception: ExceptionRecord
    payment: ExceptionPaymentContext
    validation_results: list[ValidationResultOut] = []
    notes: list[ExceptionNoteOut] = []
    assignments: list[ExceptionAssignmentOut] = []
    resolutions: list[ExceptionResolutionOut] = []
    timeline: list[TimelineEntry] = []
    approval_request: ExceptionApprovalRef | None = None
    available_actions: list[AvailableAction] = []


class ExceptionActionResponse(ExceptionDetail):
    """Updated detail after an action, plus the approval reference when one was raised."""

    approval_ref: str | None = None


class ExceptionSummaryResponse(ApiModel):
    total_open: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    by_queue: dict[str, int]


class AssignRequest(RequestModel):
    assignee_username: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class NoteRequest(RequestModel):
    body: str = Field(min_length=1, max_length=4000)
    note_type: NoteType = NoteType.COMMENT


class ExceptionActionRequest(RequestModel):
    action: ExceptionAction
    repaired_beneficiary_name: str | None = Field(default=None, min_length=1, max_length=200)
    justification: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _repair_requires_name(self) -> ExceptionActionRequest:
        if self.action is ExceptionAction.REPAIR_AND_RELEASE and not self.repaired_beneficiary_name:
            raise ValueError("repaired_beneficiary_name is required for REPAIR_AND_RELEASE")
        if self.action is not ExceptionAction.REPAIR_AND_RELEASE and self.repaired_beneficiary_name:
            raise ValueError("repaired_beneficiary_name is only accepted with REPAIR_AND_RELEASE")
        return self
