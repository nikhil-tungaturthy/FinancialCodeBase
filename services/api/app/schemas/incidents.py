"""Operational incident responses."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import IncidentSeverity, IncidentStatus
from app.schemas.common import ApiModel


class IncidentOut(ApiModel):
    incident_ref: str
    opened_at: datetime
    severity: IncidentSeverity
    status: IncidentStatus
    service: str
    title: str
    symptoms: list[str] = []
    affected_batch_ref: str | None = None
    affected_payment_refs: list[str] = []
    correlation_id: str
    evidence_path: str
    opened_by: str
    resolved_at: datetime | None = None
    resolution_summary: str | None = None


class IncidentDetail(IncidentOut):
    evidence_files: list[str] = []
