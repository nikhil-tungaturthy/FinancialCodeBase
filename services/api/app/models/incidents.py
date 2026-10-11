"""Operational incidents raised by platform tooling."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONList
from app.models.enums import IncidentSeverity, IncidentStatus


class OperationalIncident(Base):
    __tablename__ = "operational_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_ref: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    opened_at: Mapped[datetime] = mapped_column(index=True)
    severity: Mapped[IncidentSeverity]
    status: Mapped[IncidentStatus] = mapped_column(index=True)
    service: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    symptoms: Mapped[JSONList] = mapped_column(default=list)
    affected_batch_ref: Mapped[str | None] = mapped_column(String(32), index=True)
    affected_payment_refs: Mapped[JSONList] = mapped_column(default=list)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    evidence_path: Mapped[str] = mapped_column(String(255))
    opened_by: Mapped[str] = mapped_column(String(64))
    resolved_at: Mapped[datetime | None]
    resolution_summary: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"OperationalIncident(ref={self.incident_ref!r}, status={self.status.value})"
