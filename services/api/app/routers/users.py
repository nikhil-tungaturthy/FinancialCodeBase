"""Demo identities (``/api/v1/users``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.db.session import SessionDep
from app.schemas.common import Page
from app.schemas.users import UserOut
from app.services import queries

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=Page[UserOut])
def list_users(
    session: SessionDep, _user: CurrentUser, include_inactive: bool = False
) -> Page[UserOut]:
    return queries.list_users(session, include_inactive=include_inactive)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return queries.current_user_out(user)
