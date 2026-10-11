"""Classify a held payment the way the retired review desk did.

``route_exception`` (the Python reference of ``modExceptionRouting.bas``) decides
the queue, the initial severity and whether a supervisor must sign off. This
module is the only place the modern platform calls it, so the workbench and the
seed agree with the golden fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.integrations.legacy.exception_routing import RoutingResult, route_exception
from app.models.enums import ExceptionSeverity


@dataclass(frozen=True, slots=True)
class Classification:
    """Queue and severity copied onto ``payment_exceptions`` when a hold is raised."""

    queue: str
    severity: ExceptionSeverity
    requires_supervisor: bool
    legacy_reason_code: str | None
    routing: RoutingResult


def classify_exception(reason_code: str, amount_usd: Decimal, segment: str) -> Classification:
    """Route ``reason_code`` for a payment of ``amount_usd`` in ``segment``.

    ``segment`` may be a ``CustomerSegment`` value (``INSTITUTIONAL``) or the
    desk's one-character code (``I``). ``amount_usd`` must be a ``Decimal``.
    """
    routing = route_exception(reason_code, amount_usd, segment)
    return Classification(
        queue=routing.queue,
        severity=ExceptionSeverity(routing.severity_label),
        requires_supervisor=routing.requires_supervisor,
        legacy_reason_code=routing.legacy_reason_code,
        routing=routing,
    )
