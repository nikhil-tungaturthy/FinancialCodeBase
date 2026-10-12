"""Domain enumerations (``StrEnum`` so values serialise and format as plain strings)."""

from __future__ import annotations

from enum import StrEnum


class CustomerSegment(StrEnum):
    RETAIL = "RETAIL"
    CORPORATE = "CORPORATE"
    INSTITUTIONAL = "INSTITUTIONAL"
    INTERNAL = "INTERNAL"


class RiskRating(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class KycStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REVIEW_DUE = "REVIEW_DUE"
    BLOCKED = "BLOCKED"


class AccountType(StrEnum):
    OPERATING = "OPERATING"
    SETTLEMENT = "SETTLEMENT"
    TREASURY = "TREASURY"
    PERSONAL = "PERSONAL"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class Rail(StrEnum):
    WIRE_USD = "WIRE_USD"
    ACH_USD = "ACH_USD"
    SEPA_EUR = "SEPA_EUR"
    CHAPS_GBP = "CHAPS_GBP"
    SWIFT_INTL = "SWIFT_INTL"
    INTERNAL_BOOK = "INTERNAL_BOOK"


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CHF = "CHF"
    JPY = "JPY"
    SGD = "SGD"


class Channel(StrEnum):
    PORTAL = "PORTAL"
    API = "API"
    FILE = "FILE"
    BRANCH = "BRANCH"


class PaymentStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    HELD = "HELD"
    PROCESSING = "PROCESSING"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"
    SETTLED = "SETTLED"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaymentPriority(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class RiskTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PaymentEventType(StrEnum):
    CREATED = "CREATED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    HELD = "HELD"
    EXCEPTION_RAISED = "EXCEPTION_RAISED"
    REPAIRED = "REPAIRED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVED = "APPROVED"
    RELEASED = "RELEASED"
    PROCESSING = "PROCESSING"
    SUBMITTED_TO_RAIL = "SUBMITTED_TO_RAIL"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"
    SETTLED = "SETTLED"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    NOTE = "NOTE"


class ValidationOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIPPED = "SKIPPED"


class ExceptionSeverity(StrEnum):
    """Severity scale shared by exceptions, validation results and business rules."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExceptionStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ExceptionAction(StrEnum):
    REPAIR_AND_RELEASE = "REPAIR_AND_RELEASE"
    RELEASE_AS_IS = "RELEASE_AS_IS"
    RETURN_TO_CUSTOMER = "RETURN_TO_CUSTOMER"
    CANCEL_PAYMENT = "CANCEL_PAYMENT"
    ESCALATE = "ESCALATE"


class ResolutionCode(StrEnum):
    REPAIRED_RELEASED = "REPAIRED_RELEASED"
    RELEASED_AS_IS = "RELEASED_AS_IS"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"
    REJECTED_BY_APPROVER = "REJECTED_BY_APPROVER"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ApprovalSubjectType(StrEnum):
    PAYMENT_EXCEPTION = "PAYMENT_EXCEPTION"
    FEE_ADJUSTMENT = "FEE_ADJUSTMENT"
    PAYMENT_CANCELLATION = "PAYMENT_CANCELLATION"


class ApprovalRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalDecisionValue(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Role(StrEnum):
    ANALYST = "ANALYST"
    SUPERVISOR = "SUPERVISOR"
    PAYMENTS_MANAGER = "PAYMENTS_MANAGER"
    RISK_OFFICER = "RISK_OFFICER"
    ENGINEER = "ENGINEER"
    READONLY = "READONLY"


class BatchStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SUBMITTED = "SUBMITTED"
    SETTLED = "SETTLED"
    RECONCILED = "RECONCILED"
    DISCREPANCY = "DISCREPANCY"


class SettlementEntryStatus(StrEnum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


class LedgerDirection(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerLeg(StrEnum):
    PRINCIPAL = "PRINCIPAL"
    FEE = "FEE"


class PostingSource(StrEnum):
    PAYMENT_ENGINE = "PAYMENT_ENGINE"
    FEE_ENGINE = "FEE_ENGINE"
    LEGACY_BATCH = "LEGACY_BATCH"
    MANUAL = "MANUAL"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    NOT_RUN = "NOT_RUN"


class DiscrepancyKind(StrEnum):
    """Why a settlement entry and its principal credits do not match."""

    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"


class IncidentSeverity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


class NoteType(StrEnum):
    COMMENT = "COMMENT"
    EVIDENCE = "EVIDENCE"
    SYSTEM = "SYSTEM"


class BeneficiaryVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    NAME_MISMATCH_FLAGGED = "NAME_MISMATCH_FLAGGED"


class FeeType(StrEnum):
    FLAT = "FLAT"
    FLAT_PLUS_BPS = "FLAT_PLUS_BPS"


class FeeSource(StrEnum):
    MODERN = "MODERN"
    LEGACY_FEECALC01 = "LEGACY_FEECALC01"


class BusinessRuleCategory(StrEnum):
    VALIDATION = "VALIDATION"
    LIMIT = "LIMIT"
    CUTOFF = "CUTOFF"
    SCREENING = "SCREENING"
    FEE = "FEE"
    APPROVAL = "APPROVAL"


class AuditEntityType(StrEnum):
    PAYMENT = "PAYMENT"
    EXCEPTION = "EXCEPTION"
    APPROVAL = "APPROVAL"
    SETTLEMENT_BATCH = "SETTLEMENT_BATCH"
    RECONCILIATION = "RECONCILIATION"
    INCIDENT = "INCIDENT"
    POLICY = "POLICY"
    USER = "USER"
