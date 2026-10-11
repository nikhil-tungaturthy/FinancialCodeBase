"""Liveness and readiness probes (mounted at ``/`` and again under ``/api/v1``)."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Response

from app.core import clock
from app.core.config import SettingsDep
from app.db.init import check_readiness
from app.db.session import SessionDep
from app.schemas.meta import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.app_version,
        scenario_now=clock.now(),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    responses={
        HTTPStatus.SERVICE_UNAVAILABLE: {
            "model": ReadyResponse,
            "description": "Database unreachable or not seeded",
        }
    },
)
def ready(session: SessionDep, response: Response) -> ReadyResponse:
    status = check_readiness(session)
    if not status.ok:
        response.status_code = HTTPStatus.SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ready" if status.ok else "not_ready",
        database="ok" if status.database_ok else "error",
        seeded=status.seeded,
        seed_version=status.seed_version,
        detail=status.detail,
    )
