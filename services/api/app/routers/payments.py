"""Payments endpoints (``/api/v1/payments``)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, require_role
from app.db.session import SessionDep
from app.models.enums import Currency, PaymentPriority, PaymentStatus, Rail, RiskTier, Role
from app.models.users import User
from app.schemas.common import Page, RequestModel, SortOrder
from app.schemas.payments import PaymentDetail, PaymentSortField, PaymentSummary
from app.services import queries
from app.services.workflow import cancel_payment, require_payment, revalidate

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class CancelRequest(RequestModel):
    reason: str | None = None


@router.get("", response_model=Page[PaymentSummary])
def list_payments(
    session: SessionDep,
    _user: CurrentUser,
    search: str | None = None,
    status: Annotated[list[PaymentStatus] | None, Query()] = None,
    rail: Annotated[list[Rail] | None, Query()] = None,
    currency: Annotated[list[Currency] | None, Query()] = None,
    priority: Annotated[list[PaymentPriority] | None, Query()] = None,
    risk_tier: Annotated[list[RiskTier] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: PaymentSortField = "created_at",
    order: SortOrder = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[PaymentSummary]:
    return queries.list_payments(
        session,
        search=search,
        statuses=status,
        rails=rail,
        currencies=[item.value for item in currency] if currency else None,
        priorities=[item.value for item in priority] if priority else None,
        risk_tiers=[item.value for item in risk_tier] if risk_tier else None,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_ref}", response_model=PaymentDetail)
def get_payment(payment_ref: str, session: SessionDep, user: CurrentUser) -> PaymentDetail:
    return queries.get_payment(session, payment_ref, user)


@router.post("/{payment_ref}/revalidate", response_model=PaymentDetail)
def revalidate_payment(
    payment_ref: str,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.ANALYST))],
) -> PaymentDetail:
    payment = require_payment(session, payment_ref)
    revalidate(session, payment, user)
    session.flush()
    return queries.get_payment(session, payment_ref, user)


@router.post("/{payment_ref}/cancel", response_model=PaymentDetail)
def cancel(
    payment_ref: str,
    session: SessionDep,
    user: Annotated[User, Depends(require_role(Role.SUPERVISOR))],
    body: CancelRequest | None = None,
) -> PaymentDetail:
    payment = require_payment(session, payment_ref)
    cancel_payment(session, payment, user, body.reason if body else None)
    session.flush()
    return queries.get_payment(session, payment_ref, user)
