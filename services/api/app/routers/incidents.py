"""Operational incidents (``/api/v1/incidents``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.schemas.incidents import IncidentDetail, IncidentOut
from app.services import queries

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(session: SessionDep, _user: CurrentUser) -> list[IncidentOut]:
    return queries.list_incidents(session)


@router.get("/{incident_ref}", response_model=IncidentDetail)
def get_incident(incident_ref: str, session: SessionDep, _user: CurrentUser) -> IncidentDetail:
    return queries.get_incident(session, incident_ref)
