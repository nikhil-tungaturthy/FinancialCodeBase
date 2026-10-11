/**
 * Domain enumerations mirrored from `services/api/app/models/enums.py` (SPEC §3.1).
 *
 * These are string-literal unions rather than TypeScript enums so that values
 * flow through JSON untouched and remain assignable from the generated OpenAPI
 * types once `make contracts` produces `api.generated.ts`.
 */

export type CustomerSegment = 'RETAIL' | 'CORPORATE' | 'INSTITUTIONAL' | 'INTERNAL';
export type RiskRating = 'LOW' | 'MEDIUM' | 'HIGH';
export type KycStatus = 'VERIFIED' | 'REVIEW_DUE' | 'BLOCKED';
export type AccountType = 'OPERATING' | 'SETTLEMENT' | 'TREASURY' | 'PERSONAL';
export type Rail =
  'WIRE_USD' | 'ACH_USD' | 'SEPA_EUR' | 'CHAPS_GBP' | 'SWIFT_INTL' | 'INTERNAL_BOOK';
export type Currency = 'USD' | 'EUR' | 'GBP' | 'CHF' | 'JPY' | 'SGD';
export type Channel = 'PORTAL' | 'API' | 'FILE' | 'BRANCH';
export type PaymentStatus =
  | 'CREATED'
  | 'VALIDATING'
  | 'APPROVED'
  | 'HELD'
  | 'PROCESSING'
  | 'PENDING_SETTLEMENT'
  | 'SETTLED'
  | 'RECONCILED'
  | 'FAILED'
  | 'CANCELLED'
  | 'REJECTED';
export type PaymentPriority = 'NORMAL' | 'HIGH' | 'URGENT';
export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH';
export type PaymentEventType =
  | 'CREATED'
  | 'VALIDATION_STARTED'
  | 'VALIDATION_PASSED'
  | 'VALIDATION_FAILED'
  | 'HELD'
  | 'EXCEPTION_RAISED'
  | 'REPAIRED'
  | 'APPROVAL_REQUESTED'
  | 'APPROVED'
  | 'RELEASED'
  | 'PROCESSING'
  | 'SUBMITTED_TO_RAIL'
  | 'PENDING_SETTLEMENT'
  | 'SETTLED'
  | 'RECONCILED'
  | 'FAILED'
  | 'CANCELLED'
  | 'REJECTED'
  | 'NOTE';
export type ValidationOutcome = 'PASS' | 'FAIL' | 'WARN' | 'SKIPPED';
/** Open set — unknown codes (e.g. `FX_QUOTE_EXPIRED`) can and do exist. */
export type ExceptionReasonCode = string;
export type ExceptionSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ExceptionStatus =
  'OPEN' | 'IN_REVIEW' | 'PENDING_APPROVAL' | 'ESCALATED' | 'RESOLVED' | 'CANCELLED';
export type ExceptionAction =
  'REPAIR_AND_RELEASE' | 'RELEASE_AS_IS' | 'RETURN_TO_CUSTOMER' | 'CANCEL_PAYMENT' | 'ESCALATE';
export type ResolutionCode =
  | 'REPAIRED_RELEASED'
  | 'RELEASED_AS_IS'
  | 'RETURNED'
  | 'CANCELLED'
  | 'ESCALATED'
  | 'REJECTED_BY_APPROVER';
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
export type ApprovalSubjectType = 'PAYMENT_EXCEPTION' | 'FEE_ADJUSTMENT' | 'PAYMENT_CANCELLATION';
export type ApprovalRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ApprovalDecision = 'APPROVED' | 'REJECTED';
export type Role =
  'ANALYST' | 'SUPERVISOR' | 'PAYMENTS_MANAGER' | 'RISK_OFFICER' | 'ENGINEER' | 'READONLY';
export type BatchStatus =
  'OPEN' | 'CLOSED' | 'SUBMITTED' | 'SETTLED' | 'RECONCILED' | 'DISCREPANCY';
export type SettlementEntryStatus = 'PENDING' | 'SETTLED' | 'FAILED' | 'RETURNED';
export type LedgerDirection = 'DEBIT' | 'CREDIT';
export type LedgerLeg = 'PRINCIPAL' | 'FEE';
export type PostingSource = 'PAYMENT_ENGINE' | 'FEE_ENGINE' | 'LEGACY_BATCH' | 'MANUAL';
export type ReconciliationStatus = 'MATCHED' | 'UNMATCHED' | 'NOT_RUN';
export type IncidentSeverity = 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED';
export type NoteType = 'COMMENT' | 'EVIDENCE' | 'SYSTEM';
export type BeneficiaryVerificationStatus = 'VERIFIED' | 'UNVERIFIED' | 'NAME_MISMATCH_FLAGGED';
export type SettlementWindowStatus = 'OPEN' | 'CLOSED' | 'CLOSING_SOON';
export type AuditEntityType =
  | 'PAYMENT'
  | 'EXCEPTION'
  | 'APPROVAL'
  | 'SETTLEMENT_BATCH'
  | 'RECONCILIATION'
  | 'INCIDENT'
  | 'POLICY'
  | 'USER';
export type TimelineKind = 'PAYMENT_EVENT' | 'AUDIT' | 'NOTE';
export type HighPriorityKind = 'EXCEPTION' | 'INCIDENT';
export type FeeType = 'FLAT' | 'FLAT_PLUS_BPS';
export type FeeSource = 'MODERN' | 'LEGACY_FEECALC01';
export type BusinessRuleCategory =
  'VALIDATION' | 'LIMIT' | 'CUTOFF' | 'SCREENING' | 'FEE' | 'APPROVAL';

/* ------------------------------------------------------------------ */
/* Semantic tone shared by StatusPill / Badge / SeverityBadge           */
/* ------------------------------------------------------------------ */
export type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'navy' | 'teal';

/* ------------------------------------------------------------------ */
/* Labels                                                               */
/* ------------------------------------------------------------------ */
export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  CREATED: 'Created',
  VALIDATING: 'Validating',
  APPROVED: 'Approved',
  HELD: 'Held',
  PROCESSING: 'Processing',
  PENDING_SETTLEMENT: 'Pending settlement',
  SETTLED: 'Settled',
  RECONCILED: 'Reconciled',
  FAILED: 'Failed',
  CANCELLED: 'Cancelled',
  REJECTED: 'Rejected',
};

export const EXCEPTION_STATUS_LABELS: Record<ExceptionStatus, string> = {
  OPEN: 'Open',
  IN_REVIEW: 'In review',
  PENDING_APPROVAL: 'Pending approval',
  ESCALATED: 'Escalated',
  RESOLVED: 'Resolved',
  CANCELLED: 'Cancelled',
};

export const BATCH_STATUS_LABELS: Record<BatchStatus, string> = {
  OPEN: 'Open',
  CLOSED: 'Closed',
  SUBMITTED: 'Submitted',
  SETTLED: 'Settled',
  RECONCILED: 'Reconciled',
  DISCREPANCY: 'Discrepancy',
};

export const APPROVAL_STATUS_LABELS: Record<ApprovalStatus, string> = {
  PENDING: 'Pending',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  EXPIRED: 'Expired',
};

export const SEVERITY_LABELS: Record<ExceptionSeverity, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  CRITICAL: 'Critical',
};

export const PRIORITY_LABELS: Record<PaymentPriority, string> = {
  NORMAL: 'Normal',
  HIGH: 'High',
  URGENT: 'Urgent',
};

export const RISK_TIER_LABELS: Record<RiskTier, string> = {
  LOW: 'Low risk',
  MEDIUM: 'Medium risk',
  HIGH: 'High risk',
};

export const RAIL_LABELS: Record<Rail, string> = {
  WIRE_USD: 'USD Wire',
  ACH_USD: 'ACH',
  SEPA_EUR: 'SEPA',
  CHAPS_GBP: 'CHAPS',
  SWIFT_INTL: 'SWIFT',
  INTERNAL_BOOK: 'Internal book',
};

export const CHANNEL_LABELS: Record<Channel, string> = {
  PORTAL: 'Portal',
  API: 'API',
  FILE: 'File',
  BRANCH: 'Branch',
};

export const ROLE_LABELS: Record<Role, string> = {
  ANALYST: 'Analyst',
  SUPERVISOR: 'Supervisor',
  PAYMENTS_MANAGER: 'Payments manager',
  RISK_OFFICER: 'Risk officer',
  ENGINEER: 'Engineer',
  READONLY: 'Read-only',
};

export const SEGMENT_LABELS: Record<CustomerSegment, string> = {
  RETAIL: 'Retail',
  CORPORATE: 'Corporate',
  INSTITUTIONAL: 'Institutional',
  INTERNAL: 'Internal',
};

export const SETTLEMENT_ENTRY_STATUS_LABELS: Record<SettlementEntryStatus, string> = {
  PENDING: 'Pending',
  SETTLED: 'Settled',
  FAILED: 'Failed',
  RETURNED: 'Returned',
};

export const RECONCILIATION_STATUS_LABELS: Record<ReconciliationStatus, string> = {
  MATCHED: 'Matched',
  UNMATCHED: 'Unmatched',
  NOT_RUN: 'Not run',
};

export const APPROVAL_SUBJECT_LABELS: Record<ApprovalSubjectType, string> = {
  PAYMENT_EXCEPTION: 'Payment exception',
  FEE_ADJUSTMENT: 'Fee adjustment',
  PAYMENT_CANCELLATION: 'Payment cancellation',
};

export const EXCEPTION_ACTION_LABELS: Record<ExceptionAction, string> = {
  REPAIR_AND_RELEASE: 'Repair and release',
  RELEASE_AS_IS: 'Release as-is',
  RETURN_TO_CUSTOMER: 'Return to customer',
  CANCEL_PAYMENT: 'Cancel payment',
  ESCALATE: 'Escalate',
};

export const INCIDENT_STATUS_LABELS: Record<IncidentStatus, string> = {
  OPEN: 'Open',
  INVESTIGATING: 'Investigating',
  MITIGATED: 'Mitigated',
  RESOLVED: 'Resolved',
};

export const VALIDATION_OUTCOME_LABELS: Record<ValidationOutcome, string> = {
  PASS: 'Pass',
  FAIL: 'Fail',
  WARN: 'Warn',
  SKIPPED: 'Skipped',
};

/* ------------------------------------------------------------------ */
/* Tone maps                                                            */
/* ------------------------------------------------------------------ */
export const PAYMENT_STATUS_TONES: Record<PaymentStatus, Tone> = {
  CREATED: 'neutral',
  VALIDATING: 'info',
  APPROVED: 'teal',
  HELD: 'warning',
  PROCESSING: 'info',
  PENDING_SETTLEMENT: 'info',
  SETTLED: 'success',
  RECONCILED: 'success',
  FAILED: 'danger',
  CANCELLED: 'neutral',
  REJECTED: 'danger',
};

export const EXCEPTION_STATUS_TONES: Record<ExceptionStatus, Tone> = {
  OPEN: 'warning',
  IN_REVIEW: 'info',
  PENDING_APPROVAL: 'navy',
  ESCALATED: 'danger',
  RESOLVED: 'success',
  CANCELLED: 'neutral',
};

export const BATCH_STATUS_TONES: Record<BatchStatus, Tone> = {
  OPEN: 'info',
  CLOSED: 'neutral',
  SUBMITTED: 'navy',
  SETTLED: 'teal',
  RECONCILED: 'success',
  DISCREPANCY: 'danger',
};

export const APPROVAL_STATUS_TONES: Record<ApprovalStatus, Tone> = {
  PENDING: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
  EXPIRED: 'neutral',
};

export const SEVERITY_TONES: Record<ExceptionSeverity, Tone> = {
  LOW: 'neutral',
  MEDIUM: 'info',
  HIGH: 'warning',
  CRITICAL: 'danger',
};

export const PRIORITY_TONES: Record<PaymentPriority, Tone> = {
  NORMAL: 'neutral',
  HIGH: 'warning',
  URGENT: 'danger',
};

export const RISK_TIER_TONES: Record<RiskTier, Tone> = {
  LOW: 'success',
  MEDIUM: 'warning',
  HIGH: 'danger',
};

export const SETTLEMENT_ENTRY_STATUS_TONES: Record<SettlementEntryStatus, Tone> = {
  PENDING: 'info',
  SETTLED: 'success',
  FAILED: 'danger',
  RETURNED: 'warning',
};

export const RECONCILIATION_STATUS_TONES: Record<ReconciliationStatus, Tone> = {
  MATCHED: 'success',
  UNMATCHED: 'danger',
  NOT_RUN: 'neutral',
};

export const VALIDATION_OUTCOME_TONES: Record<ValidationOutcome, Tone> = {
  PASS: 'success',
  FAIL: 'danger',
  WARN: 'warning',
  SKIPPED: 'neutral',
};

export const WINDOW_STATUS_TONES: Record<SettlementWindowStatus, Tone> = {
  OPEN: 'success',
  CLOSING_SOON: 'warning',
  CLOSED: 'neutral',
};

export const INCIDENT_SEVERITY_TONES: Record<IncidentSeverity, Tone> = {
  SEV1: 'danger',
  SEV2: 'danger',
  SEV3: 'warning',
  SEV4: 'neutral',
};

/* ------------------------------------------------------------------ */
/* Option lists for filters                                             */
/* ------------------------------------------------------------------ */
export const PAYMENT_STATUSES: readonly PaymentStatus[] = Object.keys(
  PAYMENT_STATUS_LABELS,
) as PaymentStatus[];
export const EXCEPTION_STATUSES: readonly ExceptionStatus[] = Object.keys(
  EXCEPTION_STATUS_LABELS,
) as ExceptionStatus[];
export const BATCH_STATUSES: readonly BatchStatus[] = Object.keys(
  BATCH_STATUS_LABELS,
) as BatchStatus[];
export const APPROVAL_STATUSES: readonly ApprovalStatus[] = Object.keys(
  APPROVAL_STATUS_LABELS,
) as ApprovalStatus[];
export const SEVERITIES: readonly ExceptionSeverity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
export const RAILS: readonly Rail[] = Object.keys(RAIL_LABELS) as Rail[];
export const CURRENCIES: readonly Currency[] = ['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'SGD'];
export const ROLES: readonly Role[] = Object.keys(ROLE_LABELS) as Role[];

/** Human label for any enum value, falling back to a title-cased version of the raw code. */
export function humanize(code: string): string {
  return code
    .toLowerCase()
    .split('_')
    .map((part) => (part ? part[0]!.toUpperCase() + part.slice(1) : part))
    .join(' ');
}
