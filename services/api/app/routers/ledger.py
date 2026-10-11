"""Ledger entries (``/api/v1/ledger``)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.schemas.common import Page
from app.schemas.ledger import LedgerEntryOut
from app.services import queries

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


@router.get("/entries", response_model=Page[LedgerEntryOut])
def entries(
    session: SessionDep,
    _user: CurrentUser,
    payment_ref: str | None = None,
    batch_ref: str | None = None,
    journal_ref: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[LedgerEntryOut]:
    return queries.list_ledger(
        session,
        payment_ref=payment_ref,
        batch_ref=batch_ref,
        journal_ref=journal_ref,
        page=page,
        page_size=page_size,
    )
