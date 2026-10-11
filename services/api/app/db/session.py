"""Engine and session management.

``get_session`` is the FastAPI dependency; tests override it with a session bound to an
in-memory engine. SQLite connections enable foreign keys and (for file databases) WAL
journaling plus a busy timeout.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

from app.core.config import get_settings, sqlite_file_path

SQLITE_BUSY_TIMEOUT_MS = 5000

SessionLocal: sessionmaker[Session] = sessionmaker(
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)

_engine: Engine | None = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _sqlite_connect_listener(apply_wal: bool) -> Any:
    def on_connect(dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            if apply_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()

    return on_connect


def build_engine(database_url: str | None = None, *, echo: bool | None = None) -> Engine:
    """Create an engine for ``database_url`` (default: settings) with SQLite pragmas applied."""
    settings = get_settings()
    url = database_url or settings.database_url
    kwargs: dict[str, Any] = {"echo": settings.sql_echo if echo is None else echo}
    sqlite = _is_sqlite(url)
    file_path: Path | None = sqlite_file_path(url) if sqlite else None
    if sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
        if file_path is None:
            kwargs["poolclass"] = StaticPool
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if sqlite:
        event.listen(engine, "connect", _sqlite_connect_listener(apply_wal=file_path is not None))
    return engine


def configure_database(engine: Engine) -> None:
    """Bind the process-wide session factory to ``engine``."""
    global _engine
    _engine = engine
    SessionLocal.configure(bind=engine)


def get_engine() -> Engine:
    """The process-wide engine, created from settings on first use."""
    global _engine
    if _engine is None:
        configure_database(build_engine())
    assert _engine is not None
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
    SessionLocal.configure(bind=None)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session; commits on success, rolls back on error."""
    get_engine()
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """Transactional session for scripts and batch jobs."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    if engine is None:
        get_engine()
        factory = SessionLocal
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


SessionDep = Annotated[Session, Depends(get_session)]
