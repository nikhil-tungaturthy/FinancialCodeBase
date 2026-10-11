"""Role model for server-side authorisation checks.

Operations roles form a strict ladder ``ANALYST < SUPERVISOR < PAYMENTS_MANAGER``.
``RISK_OFFICER`` is a separate track that satisfies its own requirements plus anything up
to supervisor level. ``ENGINEER`` can read everything and perform analyst-level and
engineering operations but never approvals. ``READONLY`` only reads.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from app.models.enums import Role

ROLE_ORDER: Final[tuple[Role, ...]] = (Role.ANALYST, Role.SUPERVISOR, Role.PAYMENTS_MANAGER)

SATISFIES: Final[Mapping[Role, frozenset[Role]]] = {
    Role.READONLY: frozenset({Role.READONLY}),
    Role.ANALYST: frozenset({Role.READONLY, Role.ANALYST}),
    Role.SUPERVISOR: frozenset({Role.READONLY, Role.ANALYST, Role.SUPERVISOR}),
    Role.PAYMENTS_MANAGER: frozenset(
        {Role.READONLY, Role.ANALYST, Role.SUPERVISOR, Role.PAYMENTS_MANAGER}
    ),
    Role.RISK_OFFICER: frozenset({Role.READONLY, Role.ANALYST, Role.SUPERVISOR, Role.RISK_OFFICER}),
    Role.ENGINEER: frozenset({Role.READONLY, Role.ANALYST, Role.ENGINEER}),
}

ROLE_LABELS: Final[Mapping[Role, str]] = {
    Role.ANALYST: "Analyst",
    Role.SUPERVISOR: "Supervisor",
    Role.PAYMENTS_MANAGER: "Payments Manager",
    Role.RISK_OFFICER: "Risk Officer",
    Role.ENGINEER: "Engineer",
    Role.READONLY: "Read-only",
}


def as_role(value: Role | str) -> Role:
    return value if isinstance(value, Role) else Role(value.strip().upper())


def satisfies_role(user_role: Role | str, required_role: Role | str) -> bool:
    """True when ``user_role`` meets a requirement of ``required_role``."""
    return as_role(required_role) in SATISFIES[as_role(user_role)]


def satisfies_any(user_role: Role | str, required_roles: Iterable[Role | str]) -> bool:
    """True when ``user_role`` meets at least one of ``required_roles`` (empty → True)."""
    required = list(required_roles)
    if not required:
        return True
    return any(satisfies_role(user_role, role) for role in required)


def role_rank(role: Role | str) -> int:
    """Position on the operations ladder; roles outside it rank ``-1``."""
    try:
        return ROLE_ORDER.index(as_role(role))
    except ValueError:
        return -1


def role_label(role: Role | str) -> str:
    return ROLE_LABELS[as_role(role)]


def describe_requirement(required_roles: Iterable[Role | str]) -> str:
    labels = [role_label(role) for role in required_roles]
    if not labels:
        return "any role"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" or {labels[-1]}"


__all__ = [
    "ROLE_LABELS",
    "ROLE_ORDER",
    "SATISFIES",
    "Role",
    "as_role",
    "describe_requirement",
    "role_label",
    "role_rank",
    "satisfies_any",
    "satisfies_role",
]
