"""FastAPI application factory.

``uvicorn app.main:app --app-dir services/api`` serves the module-level ``app``; tests
call :func:`create_app` with their own settings and engine.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.core.config import Settings, get_settings
from app.core.errors import CORRELATION_HEADER, register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from app.db.init import init_database
from app.db.session import configure_database, get_engine
from app.routers import ALL_ROUTERS, health

APP_TITLE = "Meridian Flow API"
APP_DESCRIPTION = (
    "Global payments and exception operations for the fictional Meridian Global Bank. "
    "All data is synthetic; identity is a demo persona selected with the `X-Demo-User` "
    "header (not production authentication). Amounts are serialised as decimal strings "
    "and all timestamps are UTC."
)

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {"name": "meta", "description": "Scenario clock, seed version and FX reference rates."},
    {"name": "users", "description": "Demo identities and the current persona."},
    {"name": "overview", "description": "Operations dashboard metrics."},
    {"name": "payments", "description": "Payment search, detail and operations."},
    {"name": "exceptions", "description": "Exception queue and workbench actions."},
    {
        "name": "policies",
        "description": "Exception reason, cutoff, business rule and fee policies.",
    },
    {"name": "settlement", "description": "Settlement batches, entries and windows."},
    {"name": "ledger", "description": "General ledger postings."},
    {"name": "reconciliation", "description": "Reconciliation summary."},
    {"name": "approvals", "description": "Approval requests and decisions."},
    {"name": "audit", "description": "Audit trail search."},
    {"name": "incidents", "description": "Operational incidents and evidence."},
]


def create_app(settings: Settings | None = None, *, engine: Engine | None = None) -> FastAPI:
    """Build the application. ``engine`` overrides the settings-derived database."""
    resolved_settings = settings if settings is not None else get_settings()
    log = get_logger("meridian.app")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(
            level=resolved_settings.log_level,
            fmt=resolved_settings.log_format,
            service=resolved_settings.service_name,
        )
        db_engine = engine if engine is not None else get_engine()
        configure_database(db_engine)
        init_database(db_engine)
        application.state.engine = db_engine
        log.info(
            "app.started",
            version=resolved_settings.app_version,
            environment=resolved_settings.environment,
            scenario_now=resolved_settings.scenario_now.isoformat(),
            database=str(resolved_settings.database_path or resolved_settings.database_url),
        )
        try:
            yield
        finally:
            log.info("app.stopped")

    application = FastAPI(
        title=APP_TITLE,
        version=resolved_settings.app_version,
        description=APP_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.settings = resolved_settings

    # Middleware is applied outermost-last: CORS wraps correlation, which wraps logging.
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[CORRELATION_HEADER],
    )
    register_exception_handlers(application)

    for router in ALL_ROUTERS:
        application.include_router(router)
    # Health probes are also reachable behind the ``/api`` proxy used by the web client.
    application.include_router(health.router, prefix=resolved_settings.api_prefix)
    return application


app = create_app()
