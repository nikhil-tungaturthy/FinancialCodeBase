"""Policy documents (``/api/v1/policies``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.schemas.policies import (
    BusinessRuleOut,
    ExceptionPolicyDocument,
    FeeScheduleOut,
    SettlementCutoffPolicyDocument,
)
from app.services import queries

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.get("/exception-reasons", response_model=ExceptionPolicyDocument)
def exception_reasons(_user: CurrentUser) -> ExceptionPolicyDocument:
    return queries.exception_policy()


@router.get("/settlement-cutoffs", response_model=SettlementCutoffPolicyDocument)
def settlement_cutoffs(_user: CurrentUser) -> SettlementCutoffPolicyDocument:
    return queries.cutoff_policy()


@router.get("/business-rules", response_model=list[BusinessRuleOut])
def business_rules(session: SessionDep, _user: CurrentUser) -> list[BusinessRuleOut]:
    return queries.list_rules(session)


@router.get("/fee-schedules", response_model=list[FeeScheduleOut])
def fee_schedules(session: SessionDep, _user: CurrentUser) -> list[FeeScheduleOut]:
    return queries.list_fees(session)
