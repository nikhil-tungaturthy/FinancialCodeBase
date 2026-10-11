"""Schema creation and readiness checks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.base import Base

SEED_VERSION_KEY = "seed_version"
SEED_SCENARIO_NOW_KEY = "scenario_now"
SEED_PAYMENT_COUNT_KEY = "payment_count"
SEED_SEEDED_AT_KEY = "seeded_at"

log = get_logger(__name__)


def init_database(engine: Engine) -> None:
    """Create every table known to the metadata (idempotent)."""
    import app.models  # noqa: F401  (registers all mappers before create_all)

    Base.metadata.create_all(engine)
    log.debug("db.schema_ready", tables=len(Base.metadata.tables))


def drop_database(engine: Engine) -> None:
    """Drop every table (used by reset tooling and tests)."""
    import app.models  # noqa: F401

    Base.metadata.drop_all(engine)


@dataclass(frozen=True, slots=True)
class ReadinessStatus:
    database_ok: bool
    seeded: bool
    seed_version: str | None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.database_ok and self.seeded


def get_seed_metadata(session: Session, key: str) -> str | None:
    from app.models.meta import SeedMetadata

    return session.scalar(select(SeedMetadata.value).where(SeedMetadata.key == key))


def set_seed_metadata(session: Session, key: str, value: str) -> None:
    from app.models.meta import SeedMetadata

    existing = session.get(SeedMetadata, key)
    if existing is None:
        session.add(SeedMetadata(key=key, value=value))
    else:
        existing.value = value
    session.flush()


def check_readiness(session: Session) -> ReadinessStatus:
    """Verify connectivity and that seed metadata is present."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return ReadinessStatus(False, False, None, detail=f"database error: {type(exc).__name__}")
    try:
        seed_version = get_seed_metadata(session, SEED_VERSION_KEY)
    except SQLAlchemyError as exc:
        return ReadinessStatus(
            True, False, None, detail=f"seed metadata unavailable: {type(exc).__name__}"
        )
    if seed_version is None:
        return ReadinessStatus(True, False, None, detail="database has not been seeded")
    return ReadinessStatus(True, True, seed_version)
