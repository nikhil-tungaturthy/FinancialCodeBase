"""Payment exceptions and their assignment, note and resolution history."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.db.base import Base, JSONDict
from app.models.enums import (
    ExceptionAction,
    ExceptionSeverity,
    ExceptionStatus,
    NoteType,
    ResolutionCode,
)

if TYPE_CHECKING:
    from app.models.approvals import ApprovalRequest
    from app.models.payments import Payment
    from app.models.users import User


class PaymentException(Base):
    __tablename__ = "payment_exceptions"
    __table_args__ = (Index("ix_payment_exceptions_status_due_by", "status", "due_by"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_ref: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    reason_title: Mapped[str] = mapped_column(String(160))
    severity: Mapped[ExceptionSeverity]
    status: Mapped[ExceptionStatus] = mapped_column(index=True)
    opened_at: Mapped[datetime] = mapped_column(index=True)
    due_by: Mapped[datetime | None]
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    queue: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[str] = mapped_column(String(500))
    resolved_at: Mapped[datetime | None]
    resolution_code: Mapped[ResolutionCode | None]
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    updated_at: Mapped[datetime] = mapped_column(default=clock.now, onupdate=clock.now)

    payment: Mapped[Payment] = relationship(back_populates="exceptions")
    assigned_to: Mapped[User | None] = relationship()
    assignments: Mapped[list[ExceptionAssignment]] = relationship(
        back_populates="exception",
        order_by="ExceptionAssignment.assigned_at",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list[ExceptionNote]] = relationship(
        back_populates="exception",
        order_by="ExceptionNote.created_at",
        cascade="all, delete-orphan",
    )
    resolutions: Mapped[list[ExceptionResolution]] = relationship(
        back_populates="exception",
        order_by="ExceptionResolution.performed_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"PaymentException(ref={self.exception_ref!r}, status={self.status.value})"


class ExceptionAssignment(Base):
    __tablename__ = "exception_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("payment_exceptions.id"), index=True)
    assigned_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[str] = mapped_column(String(64))
    assigned_at: Mapped[datetime]
    note: Mapped[str | None] = mapped_column(String(500))

    exception: Mapped[PaymentException] = relationship(back_populates="assignments")
    assigned_to: Mapped[User] = relationship()


class ExceptionNote(Base):
    __tablename__ = "exception_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("payment_exceptions.id"), index=True)
    author: Mapped[str] = mapped_column(String(64))
    note_type: Mapped[NoteType] = mapped_column(default=NoteType.COMMENT)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=clock.now, index=True)

    exception: Mapped[PaymentException] = relationship(back_populates="notes")


class ExceptionResolution(Base):
    __tablename__ = "exception_resolutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("payment_exceptions.id"), index=True)
    action: Mapped[ExceptionAction]
    resolution_code: Mapped[ResolutionCode | None]
    performed_by: Mapped[str] = mapped_column(String(64))
    approval_request_id: Mapped[int | None] = mapped_column(ForeignKey("approval_requests.id"))
    performed_at: Mapped[datetime]
    details: Mapped[JSONDict] = mapped_column(default=dict)

    exception: Mapped[PaymentException] = relationship(back_populates="resolutions")
    approval_request: Mapped[ApprovalRequest | None] = relationship()
