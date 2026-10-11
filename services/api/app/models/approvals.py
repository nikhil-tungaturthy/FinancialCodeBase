"""Approval requests and decisions (four-eyes control on sensitive actions)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    ApprovalDecisionValue,
    ApprovalRiskLevel,
    ApprovalStatus,
    ApprovalSubjectType,
    Currency,
    Role,
)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_ref: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    subject_type: Mapped[ApprovalSubjectType]
    subject_ref: Mapped[str] = mapped_column(String(32), index=True)
    payment_ref: Mapped[str | None] = mapped_column(String(24), index=True)
    requested_action: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(String(500))
    justification: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[ApprovalRiskLevel]
    amount: Mapped[Decimal | None]
    currency: Mapped[Currency | None]
    requested_by: Mapped[str] = mapped_column(String(64), index=True)
    required_role: Mapped[Role]
    status: Mapped[ApprovalStatus] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(index=True)
    expires_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]

    decisions: Mapped[list[ApprovalDecision]] = relationship(
        back_populates="approval_request",
        order_by="ApprovalDecision.decided_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"ApprovalRequest(ref={self.approval_ref!r}, status={self.status.value})"


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_request_id: Mapped[int] = mapped_column(ForeignKey("approval_requests.id"), index=True)
    decided_by: Mapped[str] = mapped_column(String(64))
    decision: Mapped[ApprovalDecisionValue]
    rationale: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime]

    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="decisions")
