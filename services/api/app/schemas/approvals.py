"""Approval queue contract and decision request body."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import (
    ApprovalDecisionValue,
    ApprovalRiskLevel,
    ApprovalStatus,
    ApprovalSubjectType,
    Currency,
    Role,
)
from app.schemas.common import ApiModel, Money, RequestModel, UserRef


class ApprovalDecisionOut(ApiModel):
    decided_by: str
    decision: ApprovalDecisionValue
    rationale: str
    decided_at: datetime


class ApprovalSummary(ApiModel):
    approval_ref: str
    subject_type: ApprovalSubjectType
    subject_ref: str
    payment_ref: str | None = None
    requested_action: str
    summary: str
    risk_level: ApprovalRiskLevel
    amount: Money | None = None
    currency: Currency | None = None
    requested_by: UserRef
    required_role: Role
    status: ApprovalStatus
    is_expired: bool = False
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    decision: ApprovalDecisionOut | None = None


class CanDecide(ApiModel):
    allowed: bool
    reason: str | None = None


class ApprovalDetail(ApprovalSummary):
    justification: str
    decisions: list[ApprovalDecisionOut] = []
    can_decide: CanDecide


class ApprovalDecisionRequest(RequestModel):
    decision: ApprovalDecisionValue
    rationale: str = Field(min_length=1, max_length=2000)
