"""Query helpers for the audit trail (``audit_events``).

The repository is deliberately thin: it turns an :class:`AuditFilters` value into a
``SELECT`` and leaves normalisation, pagination bounds and error mapping to
``app.services.audit_service``. Results are always ordered newest first
(``occurred_at DESC, id DESC``) so paging is stable across identical timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.audit import AuditEvent

LIKE_ESCAPE: Final = "\\"


@dataclass(frozen=True, slots=True)
class AuditFilters:
    """Filter set for ``GET /audit``. ``None`` (or blank) means "no constraint".

    ``date_from`` / ``date_to`` are inclusive instants; naive datetimes are treated as UTC.
    ``search`` is a case-insensitive substring match over ``summary``, ``entity_ref`` and
    ``actor``.
    """

    entity_type: str | None = None
    entity_ref: str | None = None
    action: str | None = None
    actor: str | None = None
    correlation_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None

    def normalized(self) -> AuditFilters:
        """Trim whitespace, canonicalise case and normalise datetimes to UTC."""
        entity_type = _clean(self.entity_type)
        action = _clean(self.action)
        actor = _clean(self.actor)
        return AuditFilters(
            entity_type=entity_type.upper() if entity_type else None,
            entity_ref=_clean(self.entity_ref),
            action=action.upper() if action else None,
            actor=actor.lower() if actor else None,
            correlation_id=_clean(self.correlation_id),
            date_from=clock.to_utc(self.date_from) if self.date_from is not None else None,
            date_to=clock.to_utc(self.date_to) if self.date_to is not None else None,
            search=_clean(self.search),
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def escape_like(term: str) -> str:
    """Escape ``LIKE`` metacharacters so a search for ``100%`` matches literally."""
    return (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def apply_filters(
    statement: Select[tuple[AuditEvent]], filters: AuditFilters
) -> Select[tuple[AuditEvent]]:
    """Add ``WHERE`` clauses for every populated filter (filters must be normalised)."""
    if filters.entity_type:
        statement = statement.where(AuditEvent.entity_type == filters.entity_type)
    if filters.entity_ref:
        statement = statement.where(AuditEvent.entity_ref == filters.entity_ref)
    if filters.action:
        statement = statement.where(AuditEvent.action == filters.action)
    if filters.actor:
        statement = statement.where(AuditEvent.actor == filters.actor)
    if filters.correlation_id:
        statement = statement.where(AuditEvent.correlation_id == filters.correlation_id)
    if filters.date_from is not None:
        statement = statement.where(AuditEvent.occurred_at >= filters.date_from)
    if filters.date_to is not None:
        statement = statement.where(AuditEvent.occurred_at <= filters.date_to)
    if filters.search:
        pattern = f"%{escape_like(filters.search)}%"
        statement = statement.where(
            or_(
                AuditEvent.summary.ilike(pattern, escape=LIKE_ESCAPE),
                AuditEvent.entity_ref.ilike(pattern, escape=LIKE_ESCAPE),
                AuditEvent.actor.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    return statement


def _newest_first(statement: Select[tuple[AuditEvent]]) -> Select[tuple[AuditEvent]]:
    return statement.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())


def list_events(
    session: Session, filters: AuditFilters, *, offset: int, limit: int
) -> tuple[list[AuditEvent], int]:
    """One page of matching events (newest first) and the total match count."""
    base = apply_filters(select(AuditEvent), filters)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(_newest_first(base).offset(offset).limit(limit)).all()
    return list(rows), int(total)


def distinct_actions(session: Session) -> list[str]:
    """Every distinct ``action`` value present in the table, sorted alphabetically."""
    statement = select(AuditEvent.action).distinct().order_by(AuditEvent.action)
    return list(session.scalars(statement).all())


def get_by_event_id(session: Session, event_id: str) -> AuditEvent | None:
    return session.scalar(select(AuditEvent).where(AuditEvent.event_id == event_id))


def recent_events(session: Session, *, as_of: datetime, limit: int) -> list[AuditEvent]:
    """The ``limit`` most recent events that occurred at or before ``as_of``."""
    statement = select(AuditEvent).where(AuditEvent.occurred_at <= clock.to_utc(as_of))
    return list(session.scalars(_newest_first(statement).limit(limit)).all())
