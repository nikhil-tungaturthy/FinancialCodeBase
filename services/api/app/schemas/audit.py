"""Audit trail responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, Field

from app.schemas.common import ApiModel, JSONDict


class AuditEventOut(ApiModel):
    event_id: str
    occurred_at: datetime
    actor: str
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_ref: str
    summary: str
    # The ORM attribute is ``event_metadata`` (``metadata`` is reserved on the declarative
    # base); the contract name stays ``metadata``.
    metadata: JSONDict = Field(
        default_factory=dict, validation_alias=AliasChoices("event_metadata", "metadata")
    )
    correlation_id: str
    source_service: str


class AuditActionsResponse(ApiModel):
    items: list[str]
