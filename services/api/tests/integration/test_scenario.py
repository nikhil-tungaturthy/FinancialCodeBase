"""The seeded scenario answers the demo questions."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.build import run_seed
from app.seed.verify import verify_seed


def test_seed_verifies_and_serves_the_hero_and_discrepancy(
    client: TestClient, session: Session
) -> None:
    assert run_seed(session).startswith("seeded")
    session.commit()
    assert verify_seed(session) == []

    hero = client.get("/api/v1/payments/MGB-PAY-1042").json()
    assert hero["payment"]["status"] == "HELD"
    assert hero["payment"]["amount"] == "480000.00"
    assert hero["payment"]["fee_amount"] == "47.20"
    assert hero["fee"]["source"] == "LEGACY_FEECALC01"
    assert hero["exception"]["exception_ref"] == "MGB-EXC-0231"
    assert hero["exception"]["reason_code"] == "BENEFICIARY_NAME_MISMATCH"
    failed = [row["rule_code"] for row in hero["validation_results"] if row["outcome"] == "FAIL"]
    assert failed == ["VAL-001"]

    exception = client.get("/api/v1/exceptions/MGB-EXC-0231").json()
    assert exception["exception"]["queue"] == "INST-HV"
    assert exception["exception"]["severity"] == "HIGH"
    assert "guidance" not in exception

    batch = client.get("/api/v1/settlement/batches/SB-20260317-SEPA-02").json()
    assert batch["batch"]["status"] == "DISCREPANCY"
    assert Decimal(batch["batch"]["variance"]) == Decimal("18450.00")
    assert batch["reconciliation"]["run_ref"] == "RR-000061"
    assert batch["reconciliation"]["unmatched_refs"] == ["LE-002448", "LE-002452"]

    windows = client.get("/api/v1/settlement/windows").json()["windows"]
    wire = next(item for item in windows if item["rail"] == "WIRE_USD")
    assert wire["status"] == "CLOSING_SOON"
    assert wire["minutes_to_cutoff"] == 110
