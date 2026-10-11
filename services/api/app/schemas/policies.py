"""Policy documents exposed on the Policies page."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from app.models.enums import (
    BusinessRuleCategory,
    Currency,
    CustomerSegment,
    ExceptionAction,
    ExceptionSeverity,
    FeeSource,
    FeeType,
    Rail,
    Role,
)
from app.schemas.common import ApiModel, JSONDict, Money


class ReasonPolicy(ApiModel):
    reason_code: str
    title: str
    description: str
    default_severity: ExceptionSeverity
    sla_minutes: int = Field(ge=0)
    requires_approval_for_release: bool
    approval_role: Role | None = None
    approval_amount_threshold_usd: Money | None = None
    allowed_actions: list[ExceptionAction]
    required_evidence: list[str] = []
    owner_team: str
    legacy_code: str | None = None


class ExceptionPolicyDocument(ApiModel):
    version: str
    comment: str | None = None
    reasons: list[ReasonPolicy]


class SettlementCutoffPolicy(ApiModel):
    rail: Rail
    currency: Currency
    timezone: str
    cutoff_local: str
    value_date_offset_days: int = Field(ge=0)
    business_days: list[str]
    holidays: list[date] = []


class SettlementCutoffPolicyDocument(ApiModel):
    version: str | None = None
    rails: list[SettlementCutoffPolicy]


class BusinessRuleOut(ApiModel):
    rule_code: str
    name: str
    category: BusinessRuleCategory
    description: str
    severity: ExceptionSeverity
    enabled: bool
    parameters: JSONDict = {}
    owner_team: str
    legacy_origin: str | None = None


class FeeScheduleOut(ApiModel):
    rail: Rail
    currency: Currency
    segment: CustomerSegment
    fee_type: FeeType
    flat_amount: Money
    bps: int
    min_fee: Money
    max_fee: Money | None = None
    effective_from: date
    effective_to: date | None = None
    source: FeeSource
