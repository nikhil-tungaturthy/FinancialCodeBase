"""Ledger entry responses."""

from __future__ import annotations

from datetime import date, datetime

from app.models.enums import Currency, LedgerDirection, LedgerLeg, PostingSource
from app.schemas.common import ApiModel, Money


class LedgerEntryOut(ApiModel):
    entry_ref: str
    journal_ref: str
    payment_ref: str | None = None
    batch_ref: str | None = None
    account_code: str
    direction: LedgerDirection
    amount: Money
    currency: Currency
    posted_at: datetime
    value_date: date
    description: str
    posting_source: PostingSource
    leg: LedgerLeg
    correlation_id: str
