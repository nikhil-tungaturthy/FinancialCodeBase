"""Settlement batches (``/api/v1/settlement``)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser, require_role
from app.core.errors import NotFoundError
from app.db.session import SessionDep
from app.models.enums import BatchStatus, Rail, Role
from app.models.settlement import SettlementBatch
from app.models.users import User
from app.schemas.common import Page
from app.schemas.settlement import (
    BatchDetail,
    BatchSummary,
    ReconciliationResultOut,
    SettlementWindowsResponse,
)
from app.services import queries
from app.services.workflow import reconcile

router = APIRouter(prefix="/api/v1/settlement", tags=["settlement"])


@router.get("/batches", response_model=Page[BatchSummary])
def list_batches(
    session: SessionDep,
    _user: CurrentUser,
    status: Annotated[list[BatchStatus] | None, Query()] = None,
    rail: Annotated[list[Rail] | None, Query()] = None,
    value_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[BatchSummary]:
    return queries.list_batches(
        session,
        statuses=status,
        rails=rail,
        value_date=value_date,
        page=page,
        page_size=page_size,
    )


@router.get("/windows", response_model=SettlementWindowsResponse)
def windows(session: SessionDep, _user: CurrentUser) -> SettlementWindowsResponse:
    return queries.settlement_windows(session)


@router.get("/batches/{batch_ref}", response_model=BatchDetail)
def get_batch(batch_ref: str, session: SessionDep, _user: CurrentUser) -> BatchDetail:
    return queries.get_batch(session, batch_ref)


@router.post("/batches/{batch_ref}/reconcile", response_model=ReconciliationResultOut)
def reconcile_batch(
    batch_ref: str,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.ANALYST))],
) -> ReconciliationResultOut:
    batch = (
        session.scalars(
            select(SettlementBatch)
            .where(SettlementBatch.batch_ref == batch_ref)
            .options(
                selectinload(SettlementBatch.entries),
                selectinload(SettlementBatch.ledger_entries),
                selectinload(SettlementBatch.reconciliation_results),
            )
        )
        .unique()
        .one_or_none()
    )
    if batch is None:
        raise NotFoundError.for_entity("settlement batch", batch_ref)
    result = reconcile(session, batch, actor=user.username, notes=None)
    session.flush()
    from app.services.present import reconciliation_out

    return reconciliation_out(result, batch)
