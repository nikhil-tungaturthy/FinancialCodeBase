"""Scenario metadata (``/api/v1/meta``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.session import SessionDep
from app.schemas.meta import ScenarioMeta
from app.services import queries

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/scenario", response_model=ScenarioMeta)
def scenario(session: SessionDep) -> ScenarioMeta:
    return queries.scenario_meta(session)
