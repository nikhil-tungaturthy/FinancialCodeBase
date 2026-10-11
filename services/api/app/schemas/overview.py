"""Overview dashboard payload."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.schemas.audit import AuditEventOut
from app.schemas.common import ApiModel, Money
from app.schemas.settlement import SettlementWindowStatus

HighPriorityKind = Literal["EXCEPTION", "INCIDENT"]


class CurrencyValue(ApiModel):
    currency: str
    amount: Money
    count: int


class HighPriorityItem(ApiModel):
    kind: HighPriorityKind
    ref: str
    title: str
    severity: str
    due_by: datetime | None = None
    href: str


class TrendPoint(ApiModel):
    date: date
    count: int
    value_usd: Money
    exception_count: int


class QuickLink(ApiModel):
    label: str
    href: str
    count: int | None = None


class OverviewResponse(ApiModel):
    date: date
    processed_count: int
    processed_value_usd: Money
    processed_value_by_currency: list[CurrencyValue] = []
    pending_settlement_value_usd: Money
    pending_settlement_count: int
    exceptions_open_count: int
    exceptions_by_severity: dict[str, int] = {}
    high_priority_issue_count: int
    high_priority_items: list[HighPriorityItem] = []
    settlement_windows: list[SettlementWindowStatus] = []
    trend: list[TrendPoint] = []
    recent_events: list[AuditEventOut] = []
    quick_links: list[QuickLink] = []
