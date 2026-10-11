"""``record_audit_event`` writes one row per call with deterministic ids when asked."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import AuditAction, AuditEntityType, record_audit_event
from app.core.logging import bind_correlation_id, unbind
from app.models.audit import AuditEvent
from app.models.enums import Role
from app.schemas.audit import AuditEventOut


def test_records_event_with_defaults_from_scenario_clock(session: Session) -> None:
    event = record_audit_event(
        session,
        actor="priya.raman",
        action=AuditAction.EXCEPTION_NOTE_ADDED,
        entity_type=AuditEntityType.EXCEPTION,
        entity_ref="MGB-EXC-0231",
        summary="Note added",
        actor_role=Role.ANALYST,
        correlation_id="corr-pay-1042",
    )
    session.commit()

    stored = session.scalars(select(AuditEvent)).one()
    assert stored is event
    assert stored.occurred_at == datetime(2026, 3, 18, 18, 40, tzinfo=UTC)
    assert stored.action == "EXCEPTION_NOTE_ADDED"
    assert stored.entity_type == "EXCEPTION"
    assert stored.actor_role == "ANALYST"
    assert stored.source_service == "meridian-api"
    assert stored.event_metadata == {}
    assert len(stored.event_id) == 36

    out = AuditEventOut.model_validate(stored).model_dump(mode="json")
    assert out["metadata"] == {}
    assert out["entity_ref"] == "MGB-EXC-0231"


def test_stable_key_makes_event_id_deterministic(session: Session) -> None:
    kwargs = {
        "actor": "system",
        "action": "PAYMENT_CREATED",
        "entity_type": "PAYMENT",
        "entity_ref": "MGB-PAY-1042",
        "summary": "Payment received",
        "occurred_at": datetime(2026, 3, 18, 17, 52, 10, tzinfo=UTC),
        "metadata": {"seeded": True},
        "correlation_id": "corr-pay-1042",
    }
    first = record_audit_event(session, stable_key="MGB-PAY-1042:PAYMENT_CREATED:1", **kwargs)
    session.rollback()
    second = record_audit_event(session, stable_key="MGB-PAY-1042:PAYMENT_CREATED:1", **kwargs)
    other = record_audit_event(session, stable_key="MGB-PAY-1042:PAYMENT_CREATED:2", **kwargs)
    assert first.event_id == second.event_id
    assert other.event_id != first.event_id
    assert second.event_metadata == {"seeded": True}
    assert second.occurred_at == datetime(2026, 3, 18, 17, 52, 10, tzinfo=UTC)


def test_random_ids_differ_without_stable_key(session: Session) -> None:
    make = lambda: record_audit_event(  # noqa: E731
        session,
        actor="system",
        action=AuditAction.POLICY_LOADED,
        entity_type=AuditEntityType.POLICY,
        entity_ref="exception_reasons",
        summary="Policy loaded",
    )
    assert make().event_id != make().event_id


def test_unknown_action_or_entity_type_is_rejected(session: Session) -> None:
    with pytest.raises(ValueError):
        record_audit_event(
            session,
            actor="x",
            action="RECONCILIATION_INVESTIGATED",
            entity_type=AuditEntityType.RECONCILIATION,
            entity_ref="RR-1",
            summary="nope",
        )
    with pytest.raises(ValueError):
        record_audit_event(
            session,
            actor="x",
            action=AuditAction.RECONCILIATION_RUN,
            entity_type="LEDGER",
            entity_ref="RR-1",
            summary="nope",
        )


def test_correlation_id_falls_back_to_logging_context(session: Session) -> None:
    tokens = bind_correlation_id("corr-ctx-77")
    try:
        event = record_audit_event(
            session,
            actor="aisha.bello",
            action=AuditAction.RECONCILIATION_RUN,
            entity_type=AuditEntityType.SETTLEMENT_BATCH,
            entity_ref="SB-20260317-SEPA-02",
            summary="Reconciliation run",
            source_service="meridian-batch",
        )
    finally:
        unbind(tokens)
    assert event.correlation_id == "corr-ctx-77"
    assert event.source_service == "meridian-batch"
    fresh = record_audit_event(
        session,
        actor="aisha.bello",
        action=AuditAction.RECONCILIATION_RUN,
        entity_type=AuditEntityType.SETTLEMENT_BATCH,
        entity_ref="SB-20260317-SEPA-02",
        summary="Reconciliation run",
    )
    assert fresh.correlation_id.startswith("corr-req-")


def test_audit_vocabulary_is_complete() -> None:
    expected = {
        "PAYMENT_CREATED", "PAYMENT_VALIDATED", "PAYMENT_HELD", "PAYMENT_APPROVED",
        "PAYMENT_RELEASED", "PAYMENT_PROCESSING", "PAYMENT_SUBMITTED", "PAYMENT_SETTLED",
        "PAYMENT_RECONCILED", "PAYMENT_FAILED", "PAYMENT_CANCELLED", "PAYMENT_REJECTED",
        "PAYMENT_REPAIRED", "EXCEPTION_RAISED", "EXCEPTION_ASSIGNED", "EXCEPTION_NOTE_ADDED",
        "EXCEPTION_ESCALATED", "EXCEPTION_RESOLVED", "EXCEPTION_ACTION_REQUESTED",
        "APPROVAL_REQUESTED", "APPROVAL_DECIDED", "SETTLEMENT_BATCH_OPENED",
        "SETTLEMENT_BATCH_CLOSED", "SETTLEMENT_BATCH_SUBMITTED", "SETTLEMENT_BATCH_SETTLED",
        "LEDGER_POSTED", "RECONCILIATION_RUN", "INCIDENT_OPENED", "INCIDENT_UPDATED",
        "POLICY_LOADED",
    }  # fmt: skip
    assert {action.value for action in AuditAction} == expected
