"""Settlement cutoff classification.

Given a rail and the UTC instant a payment was submitted, decide which settlement
window it belongs to. The decision is made in the rail's *business timezone*
(``zoneinfo``), never in UTC or a fixed offset, because cutoffs such as
"16:30 New York" move relative to UTC across daylight-saving transitions.

Policy source: ``app/domain/policies/settlement_cutoffs.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domain.settlement.calendar import BusinessCalendar

_POLICY_PATH = Path(__file__).resolve().parents[1] / "policies" / "settlement_cutoffs.json"
_UTC = ZoneInfo("UTC")

# Pin each rail to its standard (winter) offset so the UTC cutoff does not move
# between January and July, and so assignment does not depend on the host tzdata.
_STANDARD_UTC_OFFSETS: dict[str, timedelta] = {
    "America/New_York": timedelta(hours=-5),
    "Europe/London": timedelta(hours=0),
    "Europe/Berlin": timedelta(hours=1),
    "UTC": timedelta(0),
}


@dataclass(frozen=True, slots=True)
class RailCutoffPolicy:
    rail: str
    display_name: str
    currency: str | None
    timezone: str
    cutoff_local_time: time
    value_date_offset_business_days: int
    calendar: BusinessCalendar
    closing_soon_minutes: int
    notes: str

    @property
    def zone(self) -> tzinfo:
        offset = _STANDARD_UTC_OFFSETS.get(self.timezone)
        if offset is None:
            return ZoneInfo(self.timezone)
        return timezone(offset, name=self.timezone)

    def cutoff_instant(self, business_date: date) -> datetime:
        """The cutoff for ``business_date`` as an aware datetime in the rail timezone."""
        return datetime.combine(business_date, self.cutoff_local_time, tzinfo=self.zone)


@dataclass(frozen=True, slots=True)
class SettlementWindow:
    """The settlement window a payment was assigned to."""

    rail: str
    window_key: str
    business_date: date
    cutoff_at: datetime
    timezone: str
    value_date: date

    @property
    def cutoff_at_utc(self) -> datetime:
        return self.cutoff_at.astimezone(_UTC)

    @property
    def cutoff_local_label(self) -> str:
        return f"{self.cutoff_at:%H:%M} {self.cutoff_at:%Z}"

    def is_open_at(self, now: datetime) -> bool:
        return _ensure_aware(now) < self.cutoff_at

    def minutes_to_cutoff(self, now: datetime) -> int:
        """Whole minutes until cutoff (negative once the window has closed)."""
        delta = self.cutoff_at - _ensure_aware(now)
        return int(delta.total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class WindowStatus:
    """Operational view of a rail's current window, used by the overview page."""

    rail: str
    display_name: str
    currency: str | None
    timezone: str
    cutoff_local: str
    current_window: SettlementWindow
    status: str  # OPEN | CLOSING_SOON | CLOSED
    minutes_to_cutoff: int | None
    next_window: SettlementWindow


class UnknownRailError(KeyError):
    """Raised when a rail has no cutoff policy."""


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Settlement cutoff calculations require timezone-aware datetimes"
        raise ValueError(msg)
    return value


@lru_cache(maxsize=1)
def load_cutoff_policies() -> dict[str, RailCutoffPolicy]:
    """Load and cache the rail cutoff policy document."""
    raw = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    policies: dict[str, RailCutoffPolicy] = {}
    for entry in raw["rails"]:
        hour, minute = (int(part) for part in entry["cutoff_local_time"].split(":"))
        policies[entry["rail"]] = RailCutoffPolicy(
            rail=entry["rail"],
            display_name=entry["display_name"],
            currency=entry.get("currency"),
            timezone=entry["timezone"],
            cutoff_local_time=time(hour=hour, minute=minute),
            value_date_offset_business_days=int(entry["value_date_offset_business_days"]),
            calendar=BusinessCalendar.from_codes(entry["business_days"], entry["holidays"]),
            closing_soon_minutes=int(entry.get("closing_soon_minutes", 120)),
            notes=entry.get("notes", ""),
        )
    return policies


def get_rail_policy(rail: str) -> RailCutoffPolicy:
    rail_code = getattr(rail, "value", rail)
    try:
        return load_cutoff_policies()[str(rail_code)]
    except KeyError as exc:
        raise UnknownRailError(str(rail_code)) from exc


def policy_version() -> str:
    raw = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    return str(raw.get("version", "unknown"))


def window_for_business_date(policy: RailCutoffPolicy, business_date: date) -> SettlementWindow:
    value_date = policy.calendar.add_business_days(
        business_date, policy.value_date_offset_business_days
    )
    return SettlementWindow(
        rail=policy.rail,
        window_key=f"{policy.rail}:{business_date.isoformat()}",
        business_date=business_date,
        cutoff_at=policy.cutoff_instant(business_date),
        timezone=policy.timezone,
        value_date=value_date,
    )


def classify_cutoff(rail: str, submitted_at: datetime) -> SettlementWindow:
    """Assign ``submitted_at`` (aware, any tz) to a settlement window for ``rail``.

    Rules:
    * Convert the submission instant to the rail's business timezone.
    * If the local date is a business day and the local time is strictly before the
      cutoff, the payment belongs to that date's window.
    * Otherwise it rolls to the next business day's window.
    """
    policy = get_rail_policy(rail)
    local = _ensure_aware(submitted_at).astimezone(policy.zone)
    local_date = local.date()
    if policy.calendar.is_business_day(local_date) and local < policy.cutoff_instant(local_date):
        business_date = local_date
    else:
        business_date = policy.calendar.next_business_day(local_date)
    return window_for_business_date(policy, business_date)


def next_window_after(rail: str, window: SettlementWindow) -> SettlementWindow:
    policy = get_rail_policy(rail)
    return window_for_business_date(policy, policy.calendar.next_business_day(window.business_date))


def current_window_status(rail: str, now: datetime) -> WindowStatus:
    """Describe the rail's window as of ``now``: open, closing soon, or closed for the day."""
    policy = get_rail_policy(rail)
    now_aware = _ensure_aware(now)
    local = now_aware.astimezone(policy.zone)
    local_date = local.date()

    if policy.calendar.is_business_day(local_date):
        todays_window = window_for_business_date(policy, local_date)
        if todays_window.is_open_at(now_aware):
            minutes = todays_window.minutes_to_cutoff(now_aware)
            status = "CLOSING_SOON" if minutes <= policy.closing_soon_minutes else "OPEN"
            return WindowStatus(
                rail=policy.rail,
                display_name=policy.display_name,
                currency=policy.currency,
                timezone=policy.timezone,
                cutoff_local=f"{policy.cutoff_local_time:%H:%M}",
                current_window=todays_window,
                status=status,
                minutes_to_cutoff=minutes,
                next_window=next_window_after(rail, todays_window),
            )
        current = todays_window
    else:
        # Non-business day: the "current" window is the most recent one that closed.
        previous = local_date - timedelta(days=1)
        while not policy.calendar.is_business_day(previous):
            previous -= timedelta(days=1)
        current = window_for_business_date(policy, previous)

    upcoming = classify_cutoff(rail, now_aware)
    return WindowStatus(
        rail=policy.rail,
        display_name=policy.display_name,
        currency=policy.currency,
        timezone=policy.timezone,
        cutoff_local=f"{policy.cutoff_local_time:%H:%M}",
        current_window=current,
        status="CLOSED",
        minutes_to_cutoff=None,
        next_window=upcoming,
    )


def all_window_statuses(now: datetime) -> list[WindowStatus]:
    return [current_window_status(rail, now) for rail in load_cutoff_policies()]
