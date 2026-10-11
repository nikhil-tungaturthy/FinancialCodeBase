"""FastAPI dependencies for identity and role enforcement."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.identity import get_current_user
from app.auth.roles import describe_requirement, role_label, satisfies_any
from app.core.errors import AuthorizationError
from app.models.enums import Role
from app.models.users import User

CurrentUser = Annotated[User, Depends(get_current_user)]


class RoleChecker:
    """Dependency that admits the current user only if their role satisfies one of ``roles``."""

    def __init__(self, roles: tuple[Role, ...]) -> None:
        if not roles:
            raise ValueError("require_role needs at least one role")
        self.roles = roles

    def __call__(self, user: CurrentUser) -> User:
        if not satisfies_any(user.role, self.roles):
            raise AuthorizationError(
                f"{role_label(user.role)} role may not perform this operation; "
                f"requires {describe_requirement(self.roles)}",
                context={
                    "user_role": user.role.value,
                    "required_roles": [role.value for role in self.roles],
                },
            )
        return user

    def __repr__(self) -> str:
        return f"RoleChecker({', '.join(role.value for role in self.roles)})"


def require_role(*roles: Role) -> RoleChecker:
    """``user: User = Depends(require_role(Role.SUPERVISOR))`` → 403 unless satisfied."""
    return RoleChecker(roles)


def assert_role(user: User, *roles: Role) -> None:
    """Imperative variant for service code that already holds the user."""
    RoleChecker(roles)(user)
