"""Demo identity (``X-Demo-User``) and server-side role checks. Not production auth."""

from app.auth.dependencies import CurrentUser, RoleChecker, assert_role, require_role
from app.auth.identity import DEMO_USER_HEADER, find_user, get_current_user, resolve_identity
from app.auth.roles import (
    ROLE_LABELS,
    ROLE_ORDER,
    SATISFIES,
    Role,
    as_role,
    describe_requirement,
    role_label,
    role_rank,
    satisfies_any,
    satisfies_role,
)

__all__ = [
    "DEMO_USER_HEADER",
    "ROLE_LABELS",
    "ROLE_ORDER",
    "SATISFIES",
    "CurrentUser",
    "Role",
    "RoleChecker",
    "as_role",
    "assert_role",
    "describe_requirement",
    "find_user",
    "get_current_user",
    "require_role",
    "resolve_identity",
    "role_label",
    "role_rank",
    "satisfies_any",
    "satisfies_role",
]
