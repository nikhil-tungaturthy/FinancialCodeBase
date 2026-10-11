"""Audit trail (``/api/v1/audit``)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.models.enums import AuditEntityType
from app.schemas.audit import AuditActionsResponse, AuditEventOut
from app.schemas.common import Page
from app.services import queries

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/actions", response_model=AuditActionsResponse)
def actions(_user: CurrentUser) -> AuditActionsResponse:
    return queries.audit_actions()


@router.get("", response_model=Page[AuditEventOut])
def list_events(
    session: SessionDep,
    _user: CurrentUser,
    entity_type: AuditEntityType | None = None,
    entity_ref: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    correlation_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[AuditEventOut]:
    return queries.list_audit(
        session,
        entity_type=entity_type.value if entity_type else None,
        entity_ref=entity_ref,
        action=action,
        actor=actor,
        correlation_id=correlation_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", response_model=AuditEventOut)
def get_event(event_id: str, session: SessionDep, _user: CurrentUser) -> AuditEventOut:
    return queries.get_audit_event(session, event_id)
