"""Reconciliation summary (``/api/v1/reconciliation``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.schemas.settlement import ReconciliationSummary
from app.services import queries

router = APIRouter(prefix="/api/v1/reconciliation", tags=["reconciliation"])


@router.get("/summary", response_model=ReconciliationSummary)
def summary(session: SessionDep, _user: CurrentUser) -> ReconciliationSummary:
    return queries.reconciliation_summary(session)
