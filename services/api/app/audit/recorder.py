"""Single entry point for writing audit events.

Every state-changing operation, whether it runs in the API, a batch job or the seed,
records what happened through :func:`record_audit_event`. The seed passes ``stable_key``
so event ids are reproducible (uuid5); interactive requests get a uuid4.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.audit.actions import SOURCE_API, AuditAction, AuditEntityType
from app.core import clock
from app.core.ids import new_correlation_id, stable_id
from app.core.logging import get_correlation_id, get_logger
from app.models.audit import AuditEvent
from app.models.enums import Role

log = get_logger(__name__)


def _enum_value(value: str | Enum) -> str:
    return value.value if isinstance(value, Enum) else value


def audit_event_id(stable_key: str | None) -> str:
    """Deterministic uuid5 for ``stable_key``; a uuid4 when no key is supplied."""
    if stable_key:
        return stable_id("audit-event", stable_key)
    return str(uuid.uuid4())


def record_audit_event(
    session: Session,
    *,
    actor: str,
    action: AuditAction | str,
    entity_type: AuditEntityType | str,
    entity_ref: str,
    summary: str,
    metadata: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
    actor_role: Role | str | None = None,
    source_service: str = SOURCE_API,
    occurred_at: datetime | None = None,
    stable_key: str | None = None,
) -> AuditEvent:
    """Append an :class:`AuditEvent` to ``session`` (flushed, not committed) and return it.

    ``action`` and ``entity_type`` must be members of the audit vocabulary; unknown strings
    raise ``ValueError`` so typos never reach the table.
    """
    action_value = AuditAction(_enum_value(action)).value
    entity_type_value = AuditEntityType(_enum_value(entity_type)).value
    moment = clock.to_utc(occurred_at) if occurred_at is not None else clock.now()
    resolved_correlation = correlation_id or get_correlation_id() or new_correlation_id()

    event = AuditEvent(
        event_id=audit_event_id(stable_key),
        occurred_at=moment,
        actor=actor,
        actor_role=_enum_value(actor_role) if actor_role is not None else None,
        action=action_value,
        entity_type=entity_type_value,
        entity_ref=entity_ref,
        summary=summary,
        event_metadata=dict(metadata or {}),
        correlation_id=resolved_correlation,
        source_service=source_service,
    )
    session.add(event)
    session.flush()
    log.debug(
        "audit.recorded",
        action=action_value,
        entity_type=entity_type_value,
        entity_ref=entity_ref,
        actor=actor,
        correlation_id=resolved_correlation,
    )
    return event
