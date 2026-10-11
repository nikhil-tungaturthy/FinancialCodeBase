"""Demo identity resolution via ``X-Demo-User`` and the users endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.identity import resolve_identity
from app.core.errors import AuthenticationError
from tests.conftest import DEMO_USERS, MakeUser


def test_me_defaults_to_the_demo_default_user(client: TestClient, make_user: MakeUser) -> None:
    make_user("priya.raman")
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json() == {
        "username": "priya.raman",
        "display_name": "Priya Raman",
        "email": "priya.raman@meridianglobal.example",
        "role": "ANALYST",
        "team": "Payments Operations",
        "is_active": True,
    }


def test_me_honours_header_case_insensitively(client: TestClient, make_user: MakeUser) -> None:
    make_user("marcus.okafor")
    response = client.get("/api/v1/users/me", headers={"x-demo-user": "Marcus.Okafor"})
    assert response.status_code == 200
    assert response.json()["role"] == "SUPERVISOR"


def test_unknown_identity_is_401_problem(client: TestClient, make_user: MakeUser) -> None:
    make_user("priya.raman")
    response = client.get("/api/v1/users/me", headers={"X-Demo-User": "nobody.here"})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "urn:meridian-flow:problem:unauthenticated"
    assert body["username"] == "nobody.here"
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]


def test_missing_default_user_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "priya.raman" in response.json()["detail"]


def test_inactive_identity_is_rejected(session: Session, make_user: MakeUser) -> None:
    make_user("devon.hart", is_active=False)
    try:
        resolve_identity(session, "devon.hart", "priya.raman")
    except AuthenticationError as exc:
        assert exc.status_code == 401
        assert "inactive" in exc.detail
    else:
        raise AssertionError("inactive identity must be rejected")


def test_blank_header_falls_back_to_default(session: Session, make_user: MakeUser) -> None:
    make_user("priya.raman")
    assert resolve_identity(session, "   ", "priya.raman").username == "priya.raman"


def test_users_list_is_a_page_sorted_by_username(
    client: TestClient, demo_users: dict[str, object]
) -> None:
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["total"] == len(DEMO_USERS)
    assert [item["username"] for item in body["items"]] == sorted(DEMO_USERS)
    assert body["page"] == 1


def test_users_list_hides_inactive_unless_requested(
    client: TestClient, make_user: MakeUser
) -> None:
    make_user("priya.raman")
    make_user("devon.hart", is_active=False)
    assert client.get("/api/v1/users").json()["total"] == 1
    assert client.get("/api/v1/users", params={"include_inactive": "true"}).json()["total"] == 2
