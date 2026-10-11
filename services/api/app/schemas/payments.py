"""Payment list/detail contract."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.models.enums import (
    AccountType,
    BeneficiaryVerificationStatus,
    Channel,
    Currency,
    CustomerSegment,
    ExceptionSeverity,
    ExceptionStatus,
    FeeSource,
    PaymentEventType,
    PaymentPriority,
    PaymentStatus,
    Rail,
    RiskTier,
    ValidationOutcome,
)
from app.schemas.audit import AuditEventOut
from app.schemas.common import ApiModel, JSONDict, Money

PaymentSortField = Literal["created_at", "amount", "status", "payment_ref", "customer"]


class PaymentSummary(ApiModel):
    payment_ref: str
    customer_name: str
    beneficiary_name: str
    rail: Rail
    currency: Currency
    amount: Money
    usd_equivalent: Money
    created_at: datetime
    status: PaymentStatus
    priority: PaymentPriority
    risk_tier: RiskTier
    settlement_window_key: str | None = None
    settlement_cutoff_at: datetime | None = None
    has_open_exception: bool = False
    exception_ref: str | None = None


class PaymentRecord(ApiModel):
    """Every column of the payment row (nested as ``PaymentDetail.payment``)."""

    payment_ref: str
    channel: Channel
    rail: Rail
    currency: Currency
    amount: Money
    fee_amount: Money
    fee_currency: Currency
    usd_equivalent: Money
    status: PaymentStatus
    priority: PaymentPriority
    risk_score: int
    risk_tier: RiskTier
    purpose_code: str | None = None
    end_to_end_reference: str
    remittance_info: str | None = None
    requested_value_date: date
    value_date: date
    created_at: datetime
    updated_at: datetime
    settlement_window_key: str | None = None
    settlement_cutoff_at: datetime | None = None
    settlement_timezone: str | None = None
    correlation_id: str
    idempotency_key: str
    failure_reason: str | None = None


class PaymentCustomerRef(ApiModel):
    ref: str
    name: str
    segment: CustomerSegment
    country: str


class PaymentAccountRef(ApiModel):
    ref: str
    masked_identifier: str
    currency: Currency
    account_type: AccountType


class PaymentBeneficiaryRef(ApiModel):
    ref: str
    name: str
    masked_identifier: str
    bic: str | None = None
    bank_name: str
    country: str
    verification_status: BeneficiaryVerificationStatus


class PaymentInstructionOut(ApiModel):
    channel: Channel
    instructed_beneficiary_name: str
    instructed_identifier: str
    instructed_bic: str | None = None
    instructed_bank_name: str | None = None
    instructed_country: str | None = None
    remittance_info: str | None = None
    received_at: datetime
    submitted_by: str
    raw_payload_hash: str


class FeeOut(ApiModel):
    amount: Money
    currency: Currency
    source: FeeSource


class PaymentSettlementOut(ApiModel):
    window_key: str | None = None
    cutoff_at: datetime | None = None
    timezone: str | None = None
    cutoff_local_label: str | None = None
    value_date: date
    batch_ref: str | None = None
    batch_status: str | None = None
    minutes_to_cutoff: int | None = None


class ValidationResultOut(ApiModel):
    rule_code: str
    rule_name: str
    outcome: ValidationOutcome
    severity: ExceptionSeverity
    message: str
    evidence: JSONDict = {}
    evaluated_at: datetime


class PaymentEventOut(ApiModel):
    sequence: int
    event_type: PaymentEventType
    from_status: PaymentStatus | None = None
    to_status: PaymentStatus | None = None
    occurred_at: datetime
    actor: str
    summary: str
    detail: JSONDict = {}
    correlation_id: str


class PaymentExceptionRef(ApiModel):
    exception_ref: str
    reason_code: str
    reason_title: str
    severity: ExceptionSeverity
    status: ExceptionStatus


class AvailableOperation(ApiModel):
    action: str
    label: str
    enabled: bool
    disabled_reason: str | None = None


class PaymentDetail(ApiModel):
    payment: PaymentRecord
    customer: PaymentCustomerRef
    debit_account: PaymentAccountRef
    beneficiary: PaymentBeneficiaryRef
    instruction: PaymentInstructionOut | None = None
    fee: FeeOut
    settlement: PaymentSettlementOut
    validation_results: list[ValidationResultOut] = []
    events: list[PaymentEventOut] = []
    exception: PaymentExceptionRef | None = None
    audit_events: list[AuditEventOut] = []
    available_operations: list[AvailableOperation] = []
