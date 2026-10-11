"""Every (from, to) pair of the payment lifecycle, checked against an independent table."""

from __future__ import annotations

from itertools import product

import pytest

from app.core.errors import InvalidTransitionError
from app.domain.payments.lifecycle import (
    ACTIVE_STATUSES,
    ALLOWED_TRANSITIONS,
    DEFAULT_EVENT_TYPE_FOR_STATUS,
    TERMINAL_STATUSES,
    assert_transition,
    can_transition,
    is_terminal,
    next_statuses,
)
from app.models.enums import PaymentStatus as S

# Written out by hand from the specification so the test does not simply mirror the module.
EXPECTED_ALLOWED: dict[S, set[S]] = {
    S.CREATED: {S.VALIDATING},
    S.VALIDATING: {S.APPROVED, S.HELD, S.REJECTED},
    S.HELD: {S.VALIDATING, S.APPROVED, S.CANCELLED, S.REJECTED},
    S.APPROVED: {S.PROCESSING, S.CANCELLED},
    S.PROCESSING: {S.PENDING_SETTLEMENT, S.FAILED},
    S.PENDING_SETTLEMENT: {S.SETTLED, S.FAILED},
    S.SETTLED: {S.RECONCILED},
    S.RECONCILED: set(),
    S.FAILED: set(),
    S.CANCELLED: set(),
    S.REJECTED: set(),
}

ALL_PAIRS = list(product(list(S), list(S)))


def test_every_status_has_an_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(S)
    assert set(EXPECTED_ALLOWED) == set(S)


@pytest.mark.parametrize(("source", "target"), ALL_PAIRS, ids=lambda s: s.value)
def test_can_transition_matches_specification(source: S, target: S) -> None:
    assert can_transition(source, target) is (target in EXPECTED_ALLOWED[source])


@pytest.mark.parametrize(("source", "target"), ALL_PAIRS, ids=lambda s: s.value)
def test_assert_transition_raises_409_only_for_forbidden_pairs(source: S, target: S) -> None:
    if target in EXPECTED_ALLOWED[source]:
        assert_transition(source, target, payment_ref="MGB-PAY-1042")
        return
    with pytest.raises(InvalidTransitionError) as excinfo:
        assert_transition(source, target, payment_ref="MGB-PAY-1042")
    error = excinfo.value
    assert error.status_code == 409
    assert error.from_status == source.value
    assert error.to_status == target.value
    assert "MGB-PAY-1042" in str(error)
    assert error.context["entity_ref"] == "MGB-PAY-1042"


def test_terminal_statuses() -> None:
    assert {S.RECONCILED, S.FAILED, S.CANCELLED, S.REJECTED} == TERMINAL_STATUSES
    assert all(is_terminal(status) for status in TERMINAL_STATUSES)
    assert not any(is_terminal(status) for status in ACTIVE_STATUSES)
    assert set(S) == TERMINAL_STATUSES | ACTIVE_STATUSES
    for status in TERMINAL_STATUSES:
        assert next_statuses(status) == frozenset()


def test_self_transitions_are_never_allowed() -> None:
    assert not any(can_transition(status, status) for status in S)


def test_default_event_types_cover_every_status() -> None:
    assert set(DEFAULT_EVENT_TYPE_FOR_STATUS) == set(S)
