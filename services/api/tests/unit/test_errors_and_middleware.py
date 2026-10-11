"""Correlation id middleware and the problem+json contract for every error path."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    AuthorizationError,
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    ValidationFailed,
)
from app.core.logging import get_correlation_id
from app.models.enums import PaymentStatus

PROBLEM = "application/problem+json"


class _Body(BaseModel):
    amount: str
    count: int


def _install_error_routes(app: FastAPI) -> None:
    @app.get("/_test/not-found")
    def not_found() -> None:
        raise NotFoundError.for_entity("Payment", "MGB-PAY-9999")

    @app.get("/_test/transition")
    def transition() -> None:
        raise InvalidTransitionError(
            PaymentStatus.SETTLED, PaymentStatus.HELD, entity_ref="MGB-PAY-1042"
        )

    @app.get("/_test/forbidden")
    def forbidden() -> None:
        raise AuthorizationError("Requires supervisor")

    @app.get("/_test/validation")
    def validation() -> None:
        raise ValidationFailed(
            "Beneficiary name is required", errors=[{"loc": ["body", "name"], "msg": "required"}]
        )

    @app.get("/_test/conflict")
    def conflict() -> None:
        raise ConflictError("Already assigned")

    @app.post("/_test/body")
    def body(payload: _Body) -> dict[str, str]:
        return {"amount": payload.amount}

    @app.get("/_test/context")
    def context() -> dict[str, str | None]:
        return {"correlation_id": get_correlation_id()}

    @app.get("/_test/boom")
    def boom() -> None:
        raise RuntimeError("internal-detail-must-not-leak")


def test_correlation_id_is_minted_and_echoed(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    minted = response.headers["X-Correlation-ID"]
    assert minted.startswith("corr-req-")
    second = client.get("/health").headers["X-Correlation-ID"]
    assert second != minted


def test_inbound_correlation_id_is_honoured_and_bound_to_logging_context(app: FastAPI) -> None:
    _install_error_routes(app)
    with TestClient(app) as client:
        response = client.get("/_test/context", headers={"X-Correlation-ID": "corr-pay-1042"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "corr-pay-1042"
    assert response.json() == {"correlation_id": "corr-pay-1042"}


def test_domain_errors_render_problem_json(app: FastAPI) -> None:
    _install_error_routes(app)
    with TestClient(app) as client:
        not_found = client.get("/_test/not-found", headers={"X-Correlation-ID": "corr-t-1"})
        transition = client.get("/_test/transition")
        forbidden = client.get("/_test/forbidden")
        validation = client.get("/_test/validation")
        conflict = client.get("/_test/conflict")

    assert not_found.status_code == 404
    assert not_found.headers["content-type"].startswith(PROBLEM)
    assert not_found.headers["X-Correlation-ID"] == "corr-t-1"
    body = not_found.json()
    assert body["type"] == "urn:meridian-flow:problem:not-found"
    assert body["title"] == "Resource not found"
    assert body["status"] == 404
    assert body["detail"] == "Payment MGB-PAY-9999 was not found"
    assert body["instance"] == "/_test/not-found"
    assert body["correlation_id"] == "corr-t-1"
    assert "errors" not in body

    assert transition.status_code == 409
    transition_body = transition.json()
    assert transition_body["type"] == "urn:meridian-flow:problem:invalid-transition"
    assert transition_body["from_status"] == "SETTLED"
    assert transition_body["to_status"] == "HELD"
    assert transition_body["correlation_id"] == transition.headers["X-Correlation-ID"]

    assert forbidden.status_code == 403
    assert forbidden.json()["type"] == "urn:meridian-flow:problem:forbidden"

    assert validation.status_code == 422
    assert validation.json()["errors"] == [{"loc": ["body", "name"], "msg": "required"}]

    assert conflict.status_code == 409
    assert conflict.json()["title"] == "Conflict with current state"


def test_request_validation_errors_render_problem_json(app: FastAPI) -> None:
    _install_error_routes(app)
    with TestClient(app) as client:
        response = client.post("/_test/body", json={"amount": "1.00", "count": "many"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM)
    body = response.json()
    assert body["type"] == "urn:meridian-flow:problem:request-validation"
    assert body["status"] == 422
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert body["errors"][0]["loc"] == ["body", "count"]
    assert set(body["errors"][0]) == {"loc", "msg", "type"}


def test_unknown_routes_render_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)
    body = response.json()
    assert body["type"] == "urn:meridian-flow:problem:http-404"
    assert body["title"] == "Not Found"
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]


def test_unhandled_exceptions_render_problem_json_with_correlation_id(app: FastAPI) -> None:
    _install_error_routes(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/boom", headers={"X-Correlation-ID": "corr-boom"})
    assert response.status_code == 500
    assert response.headers["content-type"].startswith(PROBLEM)
    assert response.headers["X-Correlation-ID"] == "corr-boom"
    body = response.json()
    assert body["type"] == "urn:meridian-flow:problem:internal-error"
    assert body["correlation_id"] == "corr-boom"
    assert "internal-detail-must-not-leak" not in (body["detail"] or "")


def test_cors_exposes_correlation_header(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "X-Correlation-ID" in response.headers["access-control-expose-headers"]
