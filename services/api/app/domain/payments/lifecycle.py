"""Payment lifecycle state machine.

::

    CREATED -> VALIDATING
    VALIDATING -> APPROVED | HELD | REJECTED
    HELD -> VALIDATING (after repair) | APPROVED (release) | CANCELLED | REJECTED
    APPROVED -> PROCESSING | CANCELLED
    PROCESSING -> PENDING_SETTLEMENT | FAILED
    PENDING_SETTLEMENT -> SETTLED | FAILED
    SETTLED -> RECONCILED
    terminal: RECONCILED, FAILED, CANCELLED, REJECTED

Services never assign ``payment.status`` directly; they call :func:`assert_transition`
(through ``payments_service.transition``) so an invalid move surfaces as HTTP 409.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from app.core.errors import InvalidTransitionError
from app.models.enums import PaymentEventType, PaymentStatus

ALLOWED_TRANSITIONS: Final[Mapping[PaymentStatus, frozenset[PaymentStatus]]] = {
    PaymentStatus.CREATED: frozenset({PaymentStatus.VALIDATING}),
    PaymentStatus.VALIDATING: frozenset(
        {PaymentStatus.APPROVED, PaymentStatus.HELD, PaymentStatus.REJECTED}
    ),
    PaymentStatus.HELD: frozenset(
        {
            PaymentStatus.VALIDATING,
            PaymentStatus.APPROVED,
            PaymentStatus.CANCELLED,
            PaymentStatus.REJECTED,
        }
    ),
    PaymentStatus.APPROVED: frozenset({PaymentStatus.PROCESSING, PaymentStatus.CANCELLED}),
    PaymentStatus.PROCESSING: frozenset({PaymentStatus.PENDING_SETTLEMENT, PaymentStatus.FAILED}),
    PaymentStatus.PENDING_SETTLEMENT: frozenset({PaymentStatus.SETTLED, PaymentStatus.FAILED}),
    PaymentStatus.SETTLED: frozenset({PaymentStatus.RECONCILED}),
    PaymentStatus.RECONCILED: frozenset(),
    PaymentStatus.FAILED: frozenset(),
    PaymentStatus.CANCELLED: frozenset(),
    PaymentStatus.REJECTED: frozenset(),
}

TERMINAL_STATUSES: Final[frozenset[PaymentStatus]] = frozenset(
    status for status, targets in ALLOWED_TRANSITIONS.items() if not targets
)

ACTIVE_STATUSES: Final[frozenset[PaymentStatus]] = frozenset(PaymentStatus) - TERMINAL_STATUSES

SETTLED_STATUSES: Final[frozenset[PaymentStatus]] = frozenset(
    {PaymentStatus.SETTLED, PaymentStatus.RECONCILED}
)

DEFAULT_EVENT_TYPE_FOR_STATUS: Final[Mapping[PaymentStatus, PaymentEventType]] = {
    PaymentStatus.CREATED: PaymentEventType.CREATED,
    PaymentStatus.VALIDATING: PaymentEventType.VALIDATION_STARTED,
    PaymentStatus.APPROVED: PaymentEventType.APPROVED,
    PaymentStatus.HELD: PaymentEventType.HELD,
    PaymentStatus.PROCESSING: PaymentEventType.PROCESSING,
    PaymentStatus.PENDING_SETTLEMENT: PaymentEventType.PENDING_SETTLEMENT,
    PaymentStatus.SETTLED: PaymentEventType.SETTLED,
    PaymentStatus.RECONCILED: PaymentEventType.RECONCILED,
    PaymentStatus.FAILED: PaymentEventType.FAILED,
    PaymentStatus.CANCELLED: PaymentEventType.CANCELLED,
    PaymentStatus.REJECTED: PaymentEventType.REJECTED,
}


def next_statuses(current: PaymentStatus) -> frozenset[PaymentStatus]:
    return ALLOWED_TRANSITIONS[current]


def is_terminal(status: PaymentStatus) -> bool:
    return status in TERMINAL_STATUSES


def can_transition(from_status: PaymentStatus, to_status: PaymentStatus) -> bool:
    return to_status in ALLOWED_TRANSITIONS[from_status]


def assert_transition(
    from_status: PaymentStatus,
    to_status: PaymentStatus,
    *,
    payment_ref: str | None = None,
) -> None:
    """Raise :class:`InvalidTransitionError` (HTTP 409) unless the move is allowed."""
    if not can_transition(from_status, to_status):
        raise InvalidTransitionError(
            from_status, to_status, entity="payment", entity_ref=payment_ref
        )
