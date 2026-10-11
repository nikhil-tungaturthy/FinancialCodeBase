"""Shared fixtures: in-memory SQLite engine, session, TestClient and demo users."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.init import (
    SEED_PAYMENT_COUNT_KEY,
    SEED_SCENARIO_NOW_KEY,
    SEED_VERSION_KEY,
    init_database,
    set_seed_metadata,
)
from app.db.session import SessionLocal, build_engine, get_session
from app.main import create_app
from app.models.enums import Role
from app.models.users import User

TEST_SEED_VERSION = "2026.03.1"

# Demo identities from the specification (§4).
DEMO_USERS: dict[str, dict[str, Any]] = {
    "priya.raman": {
        "display_name": "Priya Raman",
        "role": Role.ANALYST,
        "team": "Payments Operations",
    },
    "marcus.okafor": {
        "display_name": "Marcus Okafor",
        "role": Role.SUPERVISOR,
        "team": "Payments Operations",
    },
    "elena.vasquez": {
        "display_name": "Elena Vasquez",
        "role": Role.PAYMENTS_MANAGER,
        "team": "Payments Operations",
    },
    "tomasz.nowak": {
        "display_name": "Tomasz Nowak",
        "role": Role.RISK_OFFICER,
        "team": "Financial Crime Risk",
    },
    "aisha.bello": {
        "display_name": "Aisha Bello",
        "role": Role.ANALYST,
        "team": "Settlement & Reconciliation",
    },
    "devon.hart": {
        "display_name": "Devon Hart",
        "role": Role.ENGINEER,
        "team": "Payments Platform Engineering",
    },
    "system": {
        "display_name": "Meridian Flow System",
        "role": Role.ENGINEER,
        "team": "Platform",
    },
}

MakeUser = Callable[..., User]


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Settings for tests: in-memory database, quiet console logs, default scenario clock."""
    return Settings(database_url="sqlite://", log_format="console", log_level="WARNING")


@pytest.fixture
def engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite engine (StaticPool) with the full schema created."""
    test_engine = build_engine("sqlite://")
    init_database(test_engine)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine, autoflush=False, expire_on_commit=False) as db_session:
        yield db_session


@pytest.fixture
def app(settings: Settings, engine: Engine, session: Session) -> Iterator[FastAPI]:
    """Application wired to the test engine; routes share the test ``session``."""
    application = create_app(settings=settings, engine=engine)

    def override_get_session() -> Iterator[Session]:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    application.dependency_overrides[get_session] = override_get_session
    application.dependency_overrides[get_settings] = lambda: settings
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        SessionLocal.configure(bind=None)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(session: Session) -> MakeUser:
    """Insert a §4 demo user (default ``priya.raman``) and return it; fields can be overridden."""

    def factory(username: str = "priya.raman", **overrides: Any) -> User:
        try:
            profile = dict(DEMO_USERS[username])
        except KeyError as exc:
            raise ValueError(
                f"{username!r} is not a demo identity; known: {sorted(DEMO_USERS)}"
            ) from exc
        profile.update(overrides)
        user = User(
            username=username,
            display_name=profile["display_name"],
            email=profile.get("email", f"{username}@meridianglobal.example"),
            role=profile["role"],
            team=profile["team"],
            is_active=profile.get("is_active", True),
        )
        session.add(user)
        session.commit()
        return user

    return factory


@pytest.fixture
def demo_users(make_user: MakeUser) -> dict[str, User]:
    """All seven demo identities inserted; keyed by username."""
    return {username: make_user(username) for username in DEMO_USERS}


@pytest.fixture
def mark_seeded(session: Session) -> Callable[[], None]:
    """Write the seed metadata rows that make ``/ready`` report ready."""

    def apply() -> None:
        set_seed_metadata(session, SEED_VERSION_KEY, TEST_SEED_VERSION)
        set_seed_metadata(session, SEED_SCENARIO_NOW_KEY, "2026-03-18T18:40:00+00:00")
        set_seed_metadata(session, SEED_PAYMENT_COUNT_KEY, "0")
        session.commit()

    return apply
