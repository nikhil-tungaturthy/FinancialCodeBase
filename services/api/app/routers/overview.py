"""Operations overview (``/api/v1/overview``)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser
from app.core import clock
from app.db.session import SessionDep
from app.schemas.overview import OverviewResponse
from app.services import queries

router = APIRouter(prefix="/api/v1/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
def overview(
    session: SessionDep,
    _user: CurrentUser,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> OverviewResponse:
    return queries.overview(session, day or clock.today())
