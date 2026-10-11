"""Router registry. ``create_app`` includes every router in ``ALL_ROUTERS`` in order."""

from fastapi import APIRouter

from app.routers import (
    approvals,
    audit,
    exceptions,
    health,
    incidents,
    ledger,
    meta,
    overview,
    payments,
    policies,
    reconciliation,
    settlement,
    users,
)

ALL_ROUTERS: list[APIRouter] = [
    health.router,
    meta.router,
    users.router,
    overview.router,
    payments.router,
    exceptions.router,
    policies.router,
    settlement.router,
    ledger.router,
    reconciliation.router,
    approvals.router,
    audit.router,
    incidents.router,
]

__all__ = ["ALL_ROUTERS"]
