"""Approvals (``/api/v1/approvals``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.core.errors import NotFoundError
from app.db.session import SessionDep
from app.models.approvals import ApprovalRequest
from app.models.enums import ApprovalStatus
from app.schemas.approvals import ApprovalDecisionRequest, ApprovalDetail, ApprovalSummary
from app.schemas.common import Page
from app.services import queries
from app.services.workflow import decide_approval

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.get("", response_model=Page[ApprovalSummary])
def list_approvals(
    session: SessionDep,
    _user: CurrentUser,
    status: Annotated[list[ApprovalStatus] | None, Query()] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[ApprovalSummary]:
    return queries.list_approvals(
        session,
        statuses=[item.value for item in status] if status else None,
        page=page,
        page_size=page_size,
    )


@router.get("/{approval_ref}", response_model=ApprovalDetail)
def get_approval(approval_ref: str, session: SessionDep, user: CurrentUser) -> ApprovalDetail:
    return queries.get_approval(session, approval_ref, user)


@router.post("/{approval_ref}/decision", response_model=ApprovalDetail)
def decide(
    approval_ref: str,
    body: ApprovalDecisionRequest,
    session: SessionDep,
    user: CurrentUser,
) -> ApprovalDetail:
    approval = (
        session.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.approval_ref == approval_ref)
            .options(selectinload(ApprovalRequest.decisions))
        )
        .unique()
        .one_or_none()
    )
    if approval is None:
        raise NotFoundError.for_entity("approval", approval_ref)
    decide_approval(session, approval, user, body.decision, body.rationale)
    session.flush()
    return queries.get_approval(session, approval_ref, user)
