/**
 * Hand-written API contract types mirroring SPEC §9 (`/api/v1`).
 *
 * Conventions:
 *  - Monetary amounts are decimal **strings** (e.g. `"480000.00"`); never parse
 *    them into floats for arithmetic — only for display via `Intl.NumberFormat`.
 *  - Datetimes are ISO-8601 strings with offset (UTC). Dates are `YYYY-MM-DD`.
 *  - `src/types/api.generated.ts` (from `make contracts`) is the long-term
 *    source of truth; these interfaces are kept structurally compatible.
 */
import type {
  AccountType,
  ApprovalDecision,
  ApprovalRiskLevel,
  ApprovalStatus,
  ApprovalSubjectType,
  AuditEntityType,
  BatchStatus,
  BeneficiaryVerificationStatus,
  BusinessRuleCategory,
  Channel,
  Currency,
  CustomerSegment,
  ExceptionAction,
  ExceptionReasonCode,
  ExceptionSeverity,
  ExceptionStatus,
  FeeSource,
  FeeType,
  HighPriorityKind,
  IncidentSeverity,
  IncidentStatus,
  LedgerDirection,
  LedgerLeg,
  NoteType,
  PaymentEventType,
  PaymentPriority,
  PaymentStatus,
  PostingSource,
  Rail,
  ReconciliationStatus,
  ResolutionCode,
  RiskTier,
  Role,
  SettlementEntryStatus,
  SettlementWindowStatus,
  TimelineKind,
  ValidationOutcome,
} from './domain';

/** Decimal amount serialised as a string, e.g. `"480000.00"`. */
export type DecimalString = string;
/** ISO-8601 datetime with offset, e.g. `"2026-03-18T18:40:00+00:00"`. */
export type IsoDateTime = string;
/** Calendar date, `YYYY-MM-DD`. */
export type IsoDate = string;

/* ------------------------------------------------------------------ */
/* Envelope & errors                                                    */
/* ------------------------------------------------------------------ */
export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

export type SortOrder = 'asc' | 'desc';

/** RFC 9457 problem details, as emitted by the API error handlers. */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  correlation_id?: string;
  errors?: Array<{ loc?: Array<string | number>; msg: string; type?: string }>;
}

/* ------------------------------------------------------------------ */
/* Meta / health / users                                                */
/* ------------------------------------------------------------------ */
export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
  scenario_now: IsoDateTime;
}

export interface ReadyResponse {
  status: 'ready';
  database: 'ok';
  seeded: boolean;
  seed_version: string;
}

export interface ScenarioMeta {
  scenario_now: IsoDateTime;
  scenario_date: IsoDate;
  business_day_label: string;
  seed_version: string;
  display_timezone: 'UTC';
  fx_reference_rates: Record<string, DecimalString>;
  environment: 'demo' | string;
}

export interface User {
  username: string;
  display_name: string;
  email: string;
  role: Role;
  team: string;
  is_active: boolean;
}

export interface UserRef {
  username: string;
  display_name: string;
}

/* ------------------------------------------------------------------ */
/* Audit                                                                */
/* ------------------------------------------------------------------ */
export interface AuditEvent {
  event_id: string;
  occurred_at: IsoDateTime;
  actor: string;
  actor_role: Role | null;
  action: string;
  entity_type: AuditEntityType;
  entity_ref: string;
  summary: string;
  metadata: Record<string, unknown>;
  correlation_id: string;
  source_service: 'meridian-api' | 'meridian-batch' | string;
}

export interface AuditListParams extends PageParams {
  entity_type?: AuditEntityType;
  entity_ref?: string;
  action?: string;
  actor?: string;
  correlation_id?: string;
  date_from?: IsoDate;
  date_to?: IsoDate;
  search?: string;
}

/* ------------------------------------------------------------------ */
/* Overview                                                             */
/* ------------------------------------------------------------------ */
export interface CurrencyTotal {
  currency: Currency;
  amount: DecimalString;
  count: number;
}

export interface HighPriorityItem {
  kind: HighPriorityKind;
  ref: string;
  title: string;
  severity: ExceptionSeverity | IncidentSeverity;
  due_by?: IsoDateTime | null;
  href: string;
}

export interface SettlementWindow {
  rail: Rail;
  currency: Currency;
  timezone: string;
  cutoff_local: string;
  cutoff_at: IsoDateTime;
  status: SettlementWindowStatus;
  minutes_to_cutoff?: number | null;
  next_window_key: string;
  pending_count: number;
  pending_value: DecimalString;
}

export interface TrendPoint {
  date: IsoDate;
  count: number;
  value_usd: DecimalString;
  exception_count: number;
}

export interface QuickLink {
  label: string;
  href: string;
  count: number;
}

export interface Overview {
  date: IsoDate;
  processed_count: number;
  processed_value_usd: DecimalString;
  processed_value_by_currency: CurrencyTotal[];
  pending_settlement_value_usd: DecimalString;
  pending_settlement_count: number;
  exceptions_open_count: number;
  exceptions_by_severity: Partial<Record<ExceptionSeverity, number>>;
  high_priority_issue_count: number;
  high_priority_items: HighPriorityItem[];
  settlement_windows: SettlementWindow[];
  trend: TrendPoint[];
  recent_events: AuditEvent[];
  quick_links: QuickLink[];
}

/* ------------------------------------------------------------------ */
/* Payments                                                             */
/* ------------------------------------------------------------------ */
export type PaymentSortField = 'created_at' | 'amount' | 'status' | 'payment_ref' | 'customer';

export interface PaymentListParams extends PageParams {
  search?: string;
  status?: PaymentStatus[];
  rail?: Rail[];
  currency?: Currency[];
  priority?: PaymentPriority[];
  risk_tier?: RiskTier[];
  date_from?: IsoDate;
  date_to?: IsoDate;
  sort?: PaymentSortField;
  order?: SortOrder;
}

export interface PaymentSummary {
  payment_ref: string;
  customer_name: string;
  beneficiary_name: string;
  rail: Rail;
  currency: Currency;
  amount: DecimalString;
  usd_equivalent: DecimalString;
  created_at: IsoDateTime;
  status: PaymentStatus;
  priority: PaymentPriority;
  risk_tier: RiskTier;
  settlement_window_key: string | null;
  settlement_cutoff_at: IsoDateTime | null;
  has_open_exception: boolean;
  exception_ref?: string | null;
}

export interface Payment {
  payment_ref: string;
  channel: Channel;
  rail: Rail;
  currency: Currency;
  amount: DecimalString;
  fee_amount: DecimalString;
  fee_currency: Currency;
  usd_equivalent: DecimalString;
  status: PaymentStatus;
  priority: PaymentPriority;
  risk_score: number;
  risk_tier: RiskTier;
  purpose_code: string | null;
  end_to_end_reference: string;
  remittance_info: string;
  requested_value_date: IsoDate;
  value_date: IsoDate;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  settlement_window_key: string | null;
  settlement_cutoff_at: IsoDateTime | null;
  settlement_timezone: string | null;
  correlation_id: string;
  idempotency_key: string;
  failure_reason: string | null;
}

export interface CustomerRef {
  ref: string;
  name: string;
  segment: CustomerSegment;
  country: string;
}

export interface DebitAccountRef {
  ref: string;
  masked_identifier: string;
  currency: Currency;
  account_type: AccountType;
}

export interface BeneficiaryRef {
  ref: string;
  name: string;
  masked_identifier: string;
  bic: string | null;
  bank_name: string;
  country: string;
  verification_status: BeneficiaryVerificationStatus;
}

export interface PaymentInstruction {
  channel: Channel;
  instructed_beneficiary_name: string;
  instructed_identifier: string;
  instructed_bic: string | null;
  instructed_bank_name: string | null;
  instructed_country: string | null;
  remittance_info: string;
  received_at: IsoDateTime;
  submitted_by: string;
  raw_payload_hash: string;
}

export interface FeeInfo {
  amount: DecimalString;
  currency: Currency;
  source: FeeSource;
}

export interface PaymentSettlementInfo {
  window_key: string | null;
  cutoff_at: IsoDateTime | null;
  timezone: string | null;
  cutoff_local_label: string | null;
  value_date: IsoDate | null;
  batch_ref?: string | null;
  batch_status?: BatchStatus | null;
  minutes_to_cutoff?: number | null;
}

export interface ValidationResult {
  rule_code: string;
  rule_name: string;
  outcome: ValidationOutcome;
  severity: ExceptionSeverity;
  message: string;
  evidence: Record<string, unknown>;
  evaluated_at: IsoDateTime;
}

export interface PaymentEvent {
  sequence: number;
  event_type: PaymentEventType;
  from_status: PaymentStatus | null;
  to_status: PaymentStatus | null;
  occurred_at: IsoDateTime;
  actor: string;
  summary: string;
  detail: Record<string, unknown>;
  correlation_id: string;
}

export interface ExceptionRef {
  exception_ref: string;
  reason_code: ExceptionReasonCode;
  reason_title: string;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
}

export interface AvailableOperation {
  action: string;
  label: string;
  enabled: boolean;
  disabled_reason?: string | null;
}

export interface PaymentDetail {
  payment: Payment;
  customer: CustomerRef;
  debit_account: DebitAccountRef;
  beneficiary: BeneficiaryRef;
  instruction: PaymentInstruction;
  fee: FeeInfo;
  settlement: PaymentSettlementInfo;
  validation_results: ValidationResult[];
  events: PaymentEvent[];
  exception?: ExceptionRef | null;
  audit_events: AuditEvent[];
  available_operations: AvailableOperation[];
}

/* ------------------------------------------------------------------ */
/* Exceptions                                                           */
/* ------------------------------------------------------------------ */
export type ExceptionSortField = 'opened_at' | 'due_by' | 'severity' | 'amount' | 'exception_ref';

export interface ExceptionListParams extends PageParams {
  status?: ExceptionStatus[];
  severity?: ExceptionSeverity[];
  assigned_to?: string;
  queue?: string;
  search?: string;
  sort?: ExceptionSortField | string;
  order?: SortOrder;
}

export interface ExceptionQueueItem {
  exception_ref: string;
  payment_ref: string;
  reason_code: ExceptionReasonCode;
  reason_title: string;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  amount: DecimalString;
  currency: Currency;
  usd_equivalent: DecimalString;
  customer_name: string;
  opened_at: IsoDateTime;
  due_by: IsoDateTime | null;
  age_minutes: number;
  minutes_to_due?: number | null;
  assigned_to?: UserRef | null;
  queue: string;
  priority: PaymentPriority;
}

export interface ExceptionSummary {
  by_status: Partial<Record<ExceptionStatus, number>>;
  by_severity: Partial<Record<ExceptionSeverity, number>>;
  by_queue: Record<string, number>;
  total?: number;
  open_total?: number;
}

export interface PaymentException {
  exception_ref: string;
  payment_ref: string;
  reason_code: ExceptionReasonCode;
  reason_title: string;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  opened_at: IsoDateTime;
  due_by: IsoDateTime | null;
  assigned_to?: UserRef | null;
  queue: string;
  summary: string;
  resolved_at: IsoDateTime | null;
  resolution_code: ResolutionCode | null;
  correlation_id: string;
}

export interface ExceptionPaymentContext extends PaymentSummary {
  beneficiary: BeneficiaryRef;
  instruction: Pick<
    PaymentInstruction,
    | 'instructed_beneficiary_name'
    | 'instructed_identifier'
    | 'instructed_bic'
    | 'remittance_info'
    | 'received_at'
    | 'submitted_by'
  >;
}

export interface ExceptionNote {
  id?: number;
  author: string;
  note_type: NoteType;
  body: string;
  created_at: IsoDateTime;
}

export interface ExceptionAssignment {
  assigned_to: UserRef;
  assigned_by: string;
  assigned_at: IsoDateTime;
  note: string | null;
}

export interface ExceptionResolution {
  action: ExceptionAction;
  resolution_code: ResolutionCode | null;
  performed_by: string;
  approval_ref?: string | null;
  performed_at: IsoDateTime;
  details: Record<string, unknown>;
}

export interface TimelineEntry {
  occurred_at: IsoDateTime;
  kind: TimelineKind;
  title: string;
  detail: string | null;
  actor: string;
}

export interface ApprovalRequestRef {
  approval_ref: string;
  status: ApprovalStatus;
  required_role: Role;
  requested_by: string;
}

export interface AvailableAction {
  action: ExceptionAction;
  label: string;
  enabled: boolean;
  requires_approval: boolean;
  disabled_reason?: string | null;
}

export interface ExceptionDetail {
  exception: PaymentException;
  payment: ExceptionPaymentContext;
  validation_results: ValidationResult[];
  notes: ExceptionNote[];
  assignments: ExceptionAssignment[];
  resolutions: ExceptionResolution[];
  timeline: TimelineEntry[];
  approval_request?: ApprovalRequestRef | null;
  available_actions: AvailableAction[];
}

export interface AssignExceptionRequest {
  assignee_username: string;
  note?: string;
}

export interface AddExceptionNoteRequest {
  body: string;
  note_type?: NoteType;
}

export interface ExceptionActionRequest {
  action: ExceptionAction;
  repaired_beneficiary_name?: string;
  justification: string;
}

export interface ExceptionActionResponse extends ExceptionDetail {
  approval_ref?: string | null;
}

/* ------------------------------------------------------------------ */
/* Policies                                                             */
/* ------------------------------------------------------------------ */
export interface ReasonPolicy {
  reason_code: ExceptionReasonCode;
  title: string;
  description: string;
  default_severity: ExceptionSeverity;
  sla_minutes: number;
  requires_approval_for_release: boolean;
  approval_role: Role | null;
  approval_amount_threshold_usd: DecimalString | null;
  allowed_actions: ExceptionAction[];
  required_evidence: string[];
  owner_team: string;
  legacy_code: string | null;
}

export interface ExceptionReasonPolicyResponse {
  version: string;
  reasons: ReasonPolicy[];
}

export interface SettlementCutoffPolicy {
  rail: Rail;
  timezone: string;
  cutoff_local: string;
  value_date_offset_days: number;
  business_days: string[];
  holidays: IsoDate[];
}

export interface BusinessRule {
  rule_code: string;
  name: string;
  category: BusinessRuleCategory;
  description: string;
  severity: ExceptionSeverity;
  enabled: boolean;
  parameters: Record<string, unknown>;
  owner_team: string;
  legacy_origin: string | null;
}

export interface FeeSchedule {
  rail: Rail;
  currency: Currency;
  segment: CustomerSegment;
  fee_type: FeeType;
  flat_amount: DecimalString;
  bps: number;
  min_fee: DecimalString | null;
  max_fee: DecimalString | null;
  effective_from: IsoDate;
  effective_to: IsoDate | null;
  source: FeeSource;
}

/* ------------------------------------------------------------------ */
/* Settlement / ledger / reconciliation                                 */
/* ------------------------------------------------------------------ */
export interface BatchListParams extends PageParams {
  status?: BatchStatus[];
  rail?: Rail[];
  value_date?: IsoDate;
}

export interface BatchSummary {
  batch_ref: string;
  rail: Rail;
  currency: Currency;
  value_date: IsoDate;
  window_key: string;
  timezone: string;
  cutoff_at: IsoDateTime;
  status: BatchStatus;
  expected_total: DecimalString;
  recorded_total: DecimalString | null;
  variance: DecimalString | null;
  entry_count: number;
  matched_count?: number | null;
  unmatched_count?: number | null;
  reconciliation_status: ReconciliationStatus;
  settled_at: IsoDateTime | null;
}

export interface SettlementEntry {
  entry_ref: string;
  payment_ref: string | null;
  amount: DecimalString;
  currency: Currency;
  status: SettlementEntryStatus;
  external_reference: string | null;
  settled_at: IsoDateTime | null;
  matched: boolean | null;
}

export interface LedgerEntry {
  entry_ref: string;
  journal_ref: string;
  payment_ref: string | null;
  batch_ref: string | null;
  account_code: string;
  direction: LedgerDirection;
  amount: DecimalString;
  currency: Currency;
  posted_at: IsoDateTime;
  value_date: IsoDate;
  description: string;
  posting_source: PostingSource;
  leg: LedgerLeg;
  correlation_id: string;
}

export interface LedgerListParams extends PageParams {
  payment_ref?: string;
  batch_ref?: string;
  journal_ref?: string;
}

export type DiscrepancyKind = 'MISSING' | 'DUPLICATE' | 'AMOUNT_MISMATCH';

export interface ReconciliationDiscrepancy {
  kind: DiscrepancyKind;
  payment_ref: string | null;
  settlement_entry_ref: string | null;
  ledger_entry_refs: string[];
  expected_amount: DecimalString;
  recorded_amount: DecimalString;
}

export interface ReconciliationResult {
  run_ref: string;
  batch_ref: string;
  run_at: IsoDateTime;
  status: ReconciliationStatus;
  matched_count: number;
  unmatched_count: number;
  expected_total: DecimalString;
  recorded_total: DecimalString;
  variance: DecimalString;
  unmatched_refs: string[];
  discrepancies: ReconciliationDiscrepancy[];
  input_hash: string;
  notes: string | null;
}

export interface BatchDetail {
  batch: BatchSummary;
  entries: SettlementEntry[];
  ledger_entries: LedgerEntry[];
  reconciliation: ReconciliationResult | null;
  reconciliation_history: ReconciliationResult[];
}

export interface ReconciliationSummary {
  batches_total: number;
  by_status: Partial<Record<BatchStatus, number>>;
  total_variance_by_currency: Array<{ currency: Currency; variance: DecimalString }>;
  open_discrepancies: BatchSummary[];
}

/* ------------------------------------------------------------------ */
/* Approvals                                                            */
/* ------------------------------------------------------------------ */
export interface ApprovalListParams extends PageParams {
  status?: ApprovalStatus[];
}

export interface ApprovalDecisionRecord {
  decided_by: string;
  decision: ApprovalDecision;
  rationale: string;
  decided_at?: IsoDateTime;
}

export interface ApprovalSummary {
  approval_ref: string;
  subject_type: ApprovalSubjectType;
  subject_ref: string;
  payment_ref: string | null;
  requested_action: string;
  summary: string;
  risk_level: ApprovalRiskLevel;
  amount: DecimalString | null;
  currency: Currency | null;
  requested_by: UserRef;
  required_role: Role;
  status: ApprovalStatus;
  is_expired: boolean;
  created_at: IsoDateTime;
  expires_at: IsoDateTime;
  decided_at: IsoDateTime | null;
  decision?: ApprovalDecisionRecord | null;
}

export interface ApprovalDetail extends ApprovalSummary {
  justification: string;
  decisions: ApprovalDecisionRecord[];
  can_decide: { allowed: boolean; reason: string | null };
}

export interface ApprovalDecisionRequest {
  decision: ApprovalDecision;
  rationale: string;
}

/* ------------------------------------------------------------------ */
/* Incidents                                                            */
/* ------------------------------------------------------------------ */
export interface IncidentSummary {
  incident_ref: string;
  opened_at: IsoDateTime;
  severity: IncidentSeverity;
  status: IncidentStatus;
  service: string;
  title: string;
  affected_batch_ref: string | null;
  affected_payment_refs: string[];
  correlation_id: string;
  opened_by: string;
  resolved_at: IsoDateTime | null;
  resolution_summary: string | null;
}

export interface IncidentDetail extends IncidentSummary {
  symptoms: string[];
  evidence_path: string;
  evidence_files: string[];
}
