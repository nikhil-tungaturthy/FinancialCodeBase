"""Demo identity resolution.

This is **not production authentication**. The operator is chosen with the
``X-Demo-User`` header so the demo can switch personas; a missing header falls back to
``settings.demo_default_user`` and an unknown or inactive username is rejected with 401.
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import SettingsDep
from app.core.errors import AuthenticationError
from app.core.logging import bind_log_context
from app.db.session import SessionDep
from app.models.users import User

DEMO_USER_HEADER: Final = "X-Demo-User"


def find_user(session: Session, username: str) -> User | None:
    normalised = username.strip().lower()
    if not normalised:
        return None
    return session.scalar(select(User).where(User.username == normalised))


def resolve_identity(session: Session, header_value: str | None, default_username: str) -> User:
    """Return the :class:`User` for the demo header, applying the default and 401 rules."""
    requested = (header_value or "").strip() or default_username
    user = find_user(session, requested)
    if user is None:
        raise AuthenticationError(
            f"Unknown demo identity {requested!r}; set {DEMO_USER_HEADER} to a seeded username",
            context={"username": requested},
        )
    if not user.is_active:
        raise AuthenticationError(
            f"Demo identity {requested!r} is inactive", context={"username": requested}
        )
    return user


def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    x_demo_user: Annotated[
        str | None,
        Header(
            alias=DEMO_USER_HEADER,
            description="Demo persona username (not production auth). Defaults to the demo user.",
        ),
    ] = None,
) -> User:
    user = resolve_identity(session, x_demo_user, settings.demo_default_user)
    bind_log_context(actor=user.username, actor_role=user.role.value)
    return user
