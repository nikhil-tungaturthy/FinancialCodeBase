"""Liveness/readiness probes, their ``/api/v1`` aliases and the scenario meta endpoint."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import TEST_SEED_VERSION


def test_health_reports_service_version_and_scenario_clock(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "service": "meridian-api",
        "version": "0.1.0",
        "scenario_now": "2026-03-18T18:40:00Z",
    }
    assert response.headers["X-Correlation-ID"]


def test_health_is_also_mounted_under_api_prefix(client: TestClient) -> None:
    root = client.get("/health").json()
    aliased = client.get("/api/v1/health")
    assert aliased.status_code == 200
    assert aliased.json() == root


def test_ready_is_503_until_seed_metadata_exists(
    client: TestClient, mark_seeded: Callable[[], None]
) -> None:
    before = client.get("/ready")
    assert before.status_code == 503
    assert before.json() == {
        "status": "not_ready",
        "database": "ok",
        "seeded": False,
        "seed_version": None,
        "detail": "database has not been seeded",
    }

    mark_seeded()

    after = client.get("/ready")
    assert after.status_code == 200
    body = after.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["seeded"] is True
    assert body["seed_version"] == TEST_SEED_VERSION

    aliased = client.get("/api/v1/ready")
    assert aliased.status_code == 200
    assert aliased.json()["seed_version"] == TEST_SEED_VERSION


def test_scenario_meta_exposes_clock_rates_and_seed_version(
    client: TestClient, mark_seeded: Callable[[], None]
) -> None:
    unseeded = client.get("/api/v1/meta/scenario").json()
    assert unseeded["seed_version"] is None

    mark_seeded()
    response = client.get("/api/v1/meta/scenario")
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_now"] == "2026-03-18T18:40:00Z"
    assert body["scenario_date"] == "2026-03-18"
    assert body["business_day_label"] == "Wed 18 Mar 2026"
    assert body["seed_version"] == TEST_SEED_VERSION
    assert body["display_timezone"] == "UTC"
    assert body["environment"] == "demo"
    assert body["fx_rates_label"] == "scenario reference rates"
    assert body["fx_reference_rates"] == {
        "USD": "1.0000",
        "EUR": "1.0850",
        "GBP": "1.2700",
        "CHF": "1.1200",
        "JPY": "0.0067",
        "SGD": "0.7450",
    }
