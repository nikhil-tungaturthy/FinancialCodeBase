"""Money serialisation, the page envelope and guard rails on the API contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

import app.schemas as schemas
from app.models.enums import (
    Currency,
    ExceptionAction,
    PaymentPriority,
    PaymentStatus,
    Rail,
    ReconciliationStatus,
    RiskTier,
)
from app.schemas.approvals import ApprovalSummary
from app.schemas.common import Money, Page, ProblemDetails, format_money
from app.schemas.exceptions import ExceptionActionRequest, NoteRequest
from app.schemas.overview import TrendPoint
from app.schemas.payments import PaymentRecord, PaymentSummary
from app.schemas.settlement import ReconciliationResultOut
from app.schemas.users import UserOut

NOW = datetime(2026, 3, 18, 18, 40, tzinfo=UTC)


def _summary(**overrides: object) -> PaymentSummary:
    base: dict[str, object] = {
        "payment_ref": "MGB-PAY-1042",
        "customer_name": "Halvorsen Maritime Holdings AS",
        "beneficiary_name": "Corvina Steel Trading GmbH",
        "rail": Rail.WIRE_USD,
        "currency": Currency.USD,
        "amount": Decimal("480000.0000"),
        "usd_equivalent": Decimal("480000.0000"),
        "created_at": NOW,
        "status": PaymentStatus.HELD,
        "priority": PaymentPriority.URGENT,
        "risk_tier": RiskTier.MEDIUM,
    }
    base.update(overrides)
    return PaymentSummary.model_validate(base)


def test_money_fields_serialise_as_strings_with_two_decimals() -> None:
    data = _summary().model_dump(mode="json")
    assert data["amount"] == "480000.00"
    assert data["usd_equivalent"] == "480000.00"
    assert _summary().model_dump()["amount"] == Decimal("480000.0000")


def test_money_uses_sibling_currency_minor_units() -> None:
    jpy = _summary(currency=Currency.JPY, amount=Decimal("1500000.0000"), usd_equivalent="10050")
    data = jpy.model_dump(mode="json")
    assert data["amount"] == "1500000"
    assert data["usd_equivalent"] == "10050.00"


def test_fee_amount_uses_fee_currency() -> None:
    record = PaymentRecord(
        payment_ref="MGB-PAY-2001",
        channel="API",
        rail=Rail.SWIFT_INTL,
        currency=Currency.JPY,
        amount=Decimal("2500000"),
        fee_amount=Decimal("2500"),
        fee_currency=Currency.JPY,
        usd_equivalent=Decimal("16750.00"),
        status=PaymentStatus.SETTLED,
        priority=PaymentPriority.NORMAL,
        risk_score=20,
        risk_tier=RiskTier.LOW,
        end_to_end_reference="E2E-1",
        requested_value_date=NOW.date(),
        value_date=NOW.date(),
        created_at=NOW,
        updated_at=NOW,
        correlation_id="corr-pay-2001",
        idempotency_key="idem-2001",
    )
    data = record.model_dump(mode="json")
    assert data["amount"] == "2500000"
    assert data["fee_amount"] == "2500"
    assert data["usd_equivalent"] == "16750.00"


def test_optional_money_and_unknown_currency_fall_back_gracefully() -> None:
    approval = ApprovalSummary(
        approval_ref="MGB-APR-0308",
        subject_type="FEE_ADJUSTMENT",
        subject_ref="CUST-0002",
        requested_action="WAIVE_FEE",
        summary="Fee waiver",
        risk_level="LOW",
        amount=None,
        currency=None,
        requested_by={"username": "priya.raman", "display_name": "Priya Raman"},
        required_role="PAYMENTS_MANAGER",
        status="PENDING",
        created_at=NOW,
        expires_at=NOW,
    )
    assert approval.model_dump(mode="json")["amount"] is None
    trend = TrendPoint(date=NOW.date(), count=3, value_usd=Decimal("12.5"), exception_count=0)
    assert trend.model_dump(mode="json")["value_usd"] == "12.50"


def test_reconciliation_result_variance_formats_by_currency() -> None:
    result = ReconciliationResultOut(
        run_ref="RR-000012",
        batch_ref="SB-20260317-SEPA-02",
        run_at=NOW,
        status=ReconciliationStatus.UNMATCHED,
        matched_count=40,
        unmatched_count=2,
        expected_total=Decimal("412300.0000"),
        recorded_total=Decimal("430750.0000"),
        variance=Decimal("18450.0000"),
        currency=Currency.EUR,
        unmatched_refs=["LE-000388", "LE-000389"],
        input_hash="a" * 64,
    )
    data = result.model_dump(mode="json")
    assert data["variance"] == "18450.00"
    assert data["expected_total"] == "412300.00"


def test_money_json_schema_is_a_string() -> None:
    schema = PaymentSummary.model_json_schema()
    assert schema["properties"]["amount"]["type"] == "string"
    assert schema["properties"]["amount"]["examples"] == ["480000.00"]


def test_money_accepts_string_and_rejects_nonsense() -> None:
    assert _summary(amount="47.20").amount == Decimal("47.20")
    with pytest.raises(ValidationError):
        _summary(amount="lots")


def test_page_envelope() -> None:
    page = Page[UserOut].build(
        [
            UserOut(
                username="priya.raman",
                display_name="Priya Raman",
                email="priya.raman@meridianglobal.example",
                role="ANALYST",
                team="Payments Operations",
                is_active=True,
            )
        ],
        page=1,
        page_size=25,
        total=1,
    )
    data = page.model_dump(mode="json")
    assert set(data) == {"items", "page", "page_size", "total"}
    assert data["items"][0]["role"] == "ANALYST"
    with pytest.raises(ValidationError):
        Page[UserOut](items=[], page=0, page_size=25, total=0)


def test_problem_details_shape() -> None:
    problem = ProblemDetails(
        type="urn:meridian-flow:problem:not-found",
        title="Resource not found",
        status=404,
        detail="Payment MGB-PAY-9 was not found",
        instance="/api/v1/payments/MGB-PAY-9",
        correlation_id="corr-1",
    )
    assert problem.model_dump(mode="json")["errors"] is None


def test_exception_action_request_validation() -> None:
    ok = ExceptionActionRequest(
        action=ExceptionAction.REPAIR_AND_RELEASE,
        repaired_beneficiary_name="  Corvina Steel Trading GmbH ",
        justification="Callback confirmed",
    )
    assert ok.repaired_beneficiary_name == "Corvina Steel Trading GmbH"
    with pytest.raises(ValidationError, match="required for REPAIR_AND_RELEASE"):
        ExceptionActionRequest(action=ExceptionAction.REPAIR_AND_RELEASE, justification="x")
    with pytest.raises(ValidationError, match="only accepted"):
        ExceptionActionRequest(
            action=ExceptionAction.ESCALATE,
            repaired_beneficiary_name="Someone",
            justification="x",
        )
    with pytest.raises(ValidationError):
        ExceptionActionRequest(action="RELEASE_AS_IS", justification="x", extra="no")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        NoteRequest(body="   ")


def _all_schema_models() -> list[type[BaseModel]]:
    found: list[type[BaseModel]] = []
    for name in schemas.__all__:
        obj = getattr(schemas, name)
        if inspect.isclass(obj) and issubclass(obj, BaseModel):
            found.append(obj)
    return found


def test_contract_has_no_guidance_fields() -> None:
    models = _all_schema_models()
    assert len(models) > 40
    offenders = [
        f"{model.__name__}.{field}"
        for model in models
        for field in model.model_fields
        if "guidance" in field.lower() or "recommended" in field.lower()
    ]
    assert offenders == []


def test_format_money_default_matches_money_annotation() -> None:
    assert Money is not None
    assert format_money(Decimal("480000.0000")) == "480000.00"
