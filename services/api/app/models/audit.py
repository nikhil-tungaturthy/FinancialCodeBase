"""Immutable audit trail of state-changing operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONDict


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_ref"),
        Index("ix_audit_events_action_occurred_at", "action", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    actor: Mapped[str] = mapped_column(String(64), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(48))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_ref: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(String(500))
    # ``metadata`` is reserved by the declarative base, so the attribute is ``event_metadata``
    # while the column keeps the contract name.
    event_metadata: Mapped[JSONDict] = mapped_column("metadata", default=dict)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    source_service: Mapped[str] = mapped_column(String(32), default="meridian-api")

    def __repr__(self) -> str:
        return f"AuditEvent(action={self.action!r}, entity_ref={self.entity_ref!r})"
