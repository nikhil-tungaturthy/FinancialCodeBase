"""Role satisfaction matrix (§3.10) and the ``require_role`` dependency."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import assert_role, require_role
from app.auth.roles import (
    ROLE_ORDER,
    describe_requirement,
    role_rank,
    satisfies_any,
    satisfies_role,
)
from app.core.errors import AuthorizationError
from app.models.enums import Role
from app.models.users import User
from tests.conftest import MakeUser

# Rows: the user's role. Columns: the required role. Written out by hand from §3.10.
MATRIX: dict[Role, dict[Role, bool]] = {
    Role.READONLY: {
        Role.READONLY: True,
        Role.ANALYST: False,
        Role.SUPERVISOR: False,
        Role.PAYMENTS_MANAGER: False,
        Role.RISK_OFFICER: False,
        Role.ENGINEER: False,
    },
    Role.ANALYST: {
        Role.READONLY: True,
        Role.ANALYST: True,
        Role.SUPERVISOR: False,
        Role.PAYMENTS_MANAGER: False,
        Role.RISK_OFFICER: False,
        Role.ENGINEER: False,
    },
    Role.SUPERVISOR: {
        Role.READONLY: True,
        Role.ANALYST: True,
        Role.SUPERVISOR: True,
        Role.PAYMENTS_MANAGER: False,
        Role.RISK_OFFICER: False,
        Role.ENGINEER: False,
    },
    Role.PAYMENTS_MANAGER: {
        Role.READONLY: True,
        Role.ANALYST: True,
        Role.SUPERVISOR: True,
        Role.PAYMENTS_MANAGER: True,
        Role.RISK_OFFICER: False,
        Role.ENGINEER: False,
    },
    Role.RISK_OFFICER: {
        Role.READONLY: True,
        Role.ANALYST: True,
        Role.SUPERVISOR: True,
        Role.PAYMENTS_MANAGER: False,
        Role.RISK_OFFICER: True,
        Role.ENGINEER: False,
    },
    Role.ENGINEER: {
        Role.READONLY: True,
        Role.ANALYST: True,
        Role.SUPERVISOR: False,
        Role.PAYMENTS_MANAGER: False,
        Role.RISK_OFFICER: False,
        Role.ENGINEER: True,
    },
}


@pytest.mark.parametrize(
    ("user_role", "required", "expected"),
    [(u, r, ok) for u, row in MATRIX.items() for r, ok in row.items()],
    ids=lambda v: v.value if isinstance(v, Role) else str(v),
)
def test_satisfies_role_matrix(user_role: Role, required: Role, expected: bool) -> None:
    assert satisfies_role(user_role, required) is expected
    assert satisfies_role(user_role.value, required.value) is expected


def test_matrix_is_complete() -> None:
    assert set(MATRIX) == set(Role)
    assert all(set(row) == set(Role) for row in MATRIX.values())


def test_operations_ladder_order_and_rank() -> None:
    assert ROLE_ORDER == (Role.ANALYST, Role.SUPERVISOR, Role.PAYMENTS_MANAGER)
    assert role_rank(Role.ANALYST) < role_rank(Role.SUPERVISOR) < role_rank(Role.PAYMENTS_MANAGER)
    assert role_rank(Role.RISK_OFFICER) == -1
    assert role_rank(Role.ENGINEER) == -1


def test_satisfies_any() -> None:
    assert satisfies_any(Role.RISK_OFFICER, [Role.PAYMENTS_MANAGER, Role.RISK_OFFICER])
    assert not satisfies_any(Role.ANALYST, [Role.SUPERVISOR, Role.PAYMENTS_MANAGER])
    assert satisfies_any(Role.READONLY, [])


def test_describe_requirement() -> None:
    assert describe_requirement([Role.SUPERVISOR]) == "Supervisor"
    assert describe_requirement([Role.PAYMENTS_MANAGER, Role.RISK_OFFICER]) == (
        "Payments Manager or Risk Officer"
    )
    assert describe_requirement([]) == "any role"


def test_assert_role_raises_403_for_insufficient_role(make_user: MakeUser) -> None:
    priya = make_user("priya.raman")
    with pytest.raises(AuthorizationError) as excinfo:
        assert_role(priya, Role.SUPERVISOR)
    assert excinfo.value.status_code == 403
    assert excinfo.value.context["required_roles"] == ["SUPERVISOR"]
    marcus = make_user("marcus.okafor")
    assert_role(marcus, Role.SUPERVISOR)


def test_require_role_dependency_enforces_server_side(app: FastAPI, make_user: MakeUser) -> None:
    make_user("priya.raman")
    make_user("marcus.okafor")
    make_user("tomasz.nowak")
    make_user("devon.hart")

    @app.post("/_test/cancel")
    def cancel(user: User = Depends(require_role(Role.SUPERVISOR))) -> dict[str, str]:
        return {"by": user.username}

    @app.post("/_test/decide")
    def decide(
        user: User = Depends(require_role(Role.PAYMENTS_MANAGER, Role.RISK_OFFICER)),
    ) -> dict[str, str]:
        return {"by": user.username}

    with TestClient(app) as client:
        default_identity = client.post("/_test/cancel")
        assert default_identity.status_code == 403
        body = default_identity.json()
        assert body["type"] == "urn:meridian-flow:problem:forbidden"
        assert body["user_role"] == "ANALYST"
        assert body["required_roles"] == ["SUPERVISOR"]

        supervisor = client.post("/_test/cancel", headers={"X-Demo-User": "marcus.okafor"})
        assert supervisor.status_code == 200
        assert supervisor.json() == {"by": "marcus.okafor"}

        risk = client.post("/_test/decide", headers={"X-Demo-User": "tomasz.nowak"})
        assert risk.status_code == 200

        engineer = client.post("/_test/decide", headers={"X-Demo-User": "devon.hart"})
        assert engineer.status_code == 403

        supervisor_decide = client.post("/_test/decide", headers={"X-Demo-User": "marcus.okafor"})
        assert supervisor_decide.status_code == 403


def test_require_role_needs_at_least_one_role() -> None:
    with pytest.raises(ValueError):
        require_role()
