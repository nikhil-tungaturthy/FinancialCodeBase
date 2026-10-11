"""Scenario clock.

Business code never calls ``datetime.now()``. "Now" is ``settings.scenario_now`` (env
``MF_SCENARIO_NOW``), optionally overridden for a block of code with :func:`frozen`.
Only logging and request-duration measurement use the real wall clock, via
:func:`wall_clock`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, date, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

from app.core.config import get_settings

_override: ContextVar[datetime | None] = ContextVar("meridian_clock_override", default=None)


def ensure_aware(value: datetime, *, assume: tzinfo = UTC) -> datetime:
    """Return ``value`` as an aware datetime, attaching ``assume`` when it is naive."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=assume)
    return value


def to_utc(value: datetime) -> datetime:
    """Normalise an aware (or naive-as-UTC) datetime to UTC."""
    return ensure_aware(value).astimezone(UTC)


def now() -> datetime:
    """The scenario 'now' as an aware UTC datetime."""
    override = _override.get()
    if override is not None:
        return override
    return get_settings().scenario_now


def today() -> date:
    """The scenario date (UTC)."""
    return now().date()


def wall_clock() -> datetime:
    """Real current time in UTC. Reserved for log timestamps and duration measurement."""
    return datetime.now(tz=UTC)


def to_local(value: datetime, tz_name: str) -> datetime:
    """Convert an aware datetime to the IANA zone ``tz_name`` (e.g. ``America/New_York``)."""
    return to_utc(value).astimezone(ZoneInfo(tz_name))


def minutes_until(target: datetime, *, reference: datetime | None = None) -> int:
    """Whole minutes from ``reference`` (default scenario now) until ``target``.

    The result is floored, so a target 30 seconds in the past yields ``-1`` and a target
    30 seconds ahead yields ``0``. Negative values mean the target has passed.
    """
    base = to_utc(reference) if reference is not None else now()
    delta: timedelta = to_utc(target) - base
    return int(delta.total_seconds() // 60)


def age_minutes(since: datetime, *, reference: datetime | None = None) -> int:
    """Whole minutes elapsed since ``since`` (floored, never negative)."""
    base = to_utc(reference) if reference is not None else now()
    elapsed: timedelta = base - to_utc(since)
    return max(0, int(elapsed.total_seconds() // 60))


def business_day_label(value: date | datetime | None = None) -> str:
    """Format a date like ``Wed 18 Mar 2026`` (defaults to the scenario date)."""
    if value is None:
        value = today()
    elif isinstance(value, datetime):
        value = to_utc(value).date()
    return value.strftime("%a %d %b %Y")


def utc_time_label(value: datetime | None = None) -> str:
    """Format a time like ``18:40 UTC`` (defaults to scenario now)."""
    moment = to_utc(value) if value is not None else now()
    return moment.strftime("%H:%M UTC")


@contextmanager
def frozen(moment: datetime) -> Iterator[datetime]:
    """Temporarily pin :func:`now` to ``moment`` for the enclosed block (tests, replays)."""
    pinned = to_utc(moment)
    token = _override.set(pinned)
    try:
        yield pinned
    finally:
        _override.reset(token)
