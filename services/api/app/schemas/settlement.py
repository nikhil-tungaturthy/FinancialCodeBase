"""Settlement batches, reconciliation results and windows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.models.enums import (
    BatchStatus,
    Currency,
    DiscrepancyKind,
    Rail,
    ReconciliationStatus,
    SettlementEntryStatus,
)
from app.schemas.common import ApiModel, Money, RequestModel
from app.schemas.ledger import LedgerEntryOut

WindowState = Literal["OPEN", "CLOSED", "CLOSING_SOON"]


class BatchSummary(ApiModel):
    batch_ref: str
    rail: Rail
    currency: Currency
    value_date: date
    window_key: str
    timezone: str
    cutoff_at: datetime
    status: BatchStatus
    expected_total: Money
    recorded_total: Money | None = None
    variance: Money | None = None
    entry_count: int
    matched_count: int | None = None
    unmatched_count: int | None = None
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.NOT_RUN
    settled_at: datetime | None = None


class SettlementEntryOut(ApiModel):
    entry_ref: str
    payment_ref: str | None = None
    amount: Money
    currency: Currency
    status: SettlementEntryStatus
    external_reference: str | None = None
    settled_at: datetime | None = None
    matched: bool | None = None
    sequence: int


class DiscrepancyOut(ApiModel):
    kind: DiscrepancyKind
    payment_ref: str | None = None
    settlement_entry_ref: str | None = None
    ledger_entry_refs: list[str] = []
    expected_amount: Money
    recorded_amount: Money


class ReconciliationResultOut(ApiModel):
    run_ref: str
    batch_ref: str
    run_at: datetime
    status: ReconciliationStatus
    matched_count: int
    unmatched_count: int
    expected_total: Money
    recorded_total: Money
    variance: Money
    currency: Currency
    unmatched_refs: list[str] = []
    discrepancies: list[DiscrepancyOut] = []
    input_hash: str
    notes: str | None = None


class BatchDetail(ApiModel):
    batch: BatchSummary
    entries: list[SettlementEntryOut] = []
    ledger_entries: list[LedgerEntryOut] = []
    reconciliation: ReconciliationResultOut | None = None
    reconciliation_history: list[ReconciliationResultOut] = []


class ReconcileRequest(RequestModel):
    notes: str | None = Field(default=None, max_length=1000)


class SettlementWindowStatus(ApiModel):
    rail: Rail
    currency: Currency
    timezone: str
    cutoff_local: str
    cutoff_at: datetime
    status: WindowState
    minutes_to_cutoff: int | None = None
    next_window_key: str
    pending_count: int
    pending_value: Money


class SettlementWindowsResponse(ApiModel):
    as_of: datetime
    windows: list[SettlementWindowStatus]


class CurrencyVariance(ApiModel):
    currency: Currency
    variance: Money
    batch_count: int


class ReconciliationSummary(ApiModel):
    batches_total: int
    by_status: dict[str, int]
    total_variance_by_currency: list[CurrencyVariance] = []
    open_discrepancies: list[BatchSummary] = []
