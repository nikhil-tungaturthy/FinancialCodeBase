"""Cutoff classification tests.

Dates in these tests are chosen in January 2026 (standard time in every rail timezone)
plus weekend and holiday rolling cases, and the UTC-based INTERNAL_BOOK rail.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.domain.settlement.cutoff import (
    UnknownRailError,
    all_window_statuses,
    classify_cutoff,
    current_window_status,
    get_rail_policy,
    load_cutoff_policies,
)

NY = ZoneInfo("America/New_York")
LON = ZoneInfo("Europe/London")
FRA = ZoneInfo("Europe/Berlin")


def utc(y: int, m: int, d: int, hh: int, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def test_policy_loads_all_rails() -> None:
    policies = load_cutoff_policies()
    assert set(policies) == {
        "WIRE_USD",
        "ACH_USD",
        "SEPA_EUR",
        "CHAPS_GBP",
        "SWIFT_INTL",
        "INTERNAL_BOOK",
    }
    assert get_rail_policy("WIRE_USD").timezone == "America/New_York"


def test_unknown_rail_raises() -> None:
    with pytest.raises(UnknownRailError):
        get_rail_policy("CARRIER_PIGEON")


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        classify_cutoff("WIRE_USD", datetime(2026, 1, 14, 12, 0))


def test_wire_usd_before_cutoff_is_same_day() -> None:
    # 14 Jan 2026 (Wed) 15:45 New York = 20:45Z — before the 16:30 cutoff.
    window = classify_cutoff("WIRE_USD", utc(2026, 1, 14, 20, 45))
    assert window.business_date == date(2026, 1, 14)
    assert window.window_key == "WIRE_USD:2026-01-14"
    assert window.cutoff_at == datetime(2026, 1, 14, 16, 30, tzinfo=NY)
    assert window.cutoff_at_utc == utc(2026, 1, 14, 21, 30)
    assert window.value_date == date(2026, 1, 14)
    assert window.timezone == "America/New_York"


def test_wire_usd_at_exact_cutoff_rolls_to_next_day() -> None:
    window = classify_cutoff("WIRE_USD", utc(2026, 1, 14, 21, 30))
    assert window.business_date == date(2026, 1, 15)


def test_wire_usd_one_minute_before_cutoff_is_same_day() -> None:
    window = classify_cutoff("WIRE_USD", utc(2026, 1, 14, 21, 29))
    assert window.business_date == date(2026, 1, 14)


def test_friday_after_cutoff_rolls_to_monday() -> None:
    # Fri 16 Jan 2026 17:00 New York (22:00Z) → Mon 19 Jan is MLK holiday → Tue 20 Jan.
    window = classify_cutoff("WIRE_USD", utc(2026, 1, 16, 22, 0))
    assert window.business_date == date(2026, 1, 20)
    assert window.value_date == date(2026, 1, 20)


def test_saturday_submission_rolls_to_next_business_day() -> None:
    window = classify_cutoff("CHAPS_GBP", utc(2026, 1, 10, 9, 0))  # Saturday
    assert window.business_date == date(2026, 1, 12)


def test_ach_value_date_is_next_business_day() -> None:
    window = classify_cutoff("ACH_USD", utc(2026, 1, 14, 15, 0))
    assert window.business_date == date(2026, 1, 14)
    assert window.value_date == date(2026, 1, 15)


def test_swift_offset_skips_weekend() -> None:
    # Fri 16 Jan 2026 10:00 London → window Fri, value date Mon 19 Jan (UK calendar, no holiday).
    window = classify_cutoff("SWIFT_INTL", utc(2026, 1, 16, 10, 0))
    assert window.business_date == date(2026, 1, 16)
    assert window.value_date == date(2026, 1, 19)


def test_sepa_cutoff_uses_frankfurt_local_time() -> None:
    # 14 Jan 2026 15:30Z = 16:30 Frankfurt (CET) → after the 16:00 cutoff → next day.
    window = classify_cutoff("SEPA_EUR", utc(2026, 1, 14, 15, 30))
    assert window.business_date == date(2026, 1, 15)
    # 14:59Z = 15:59 Frankfurt → same day.
    assert classify_cutoff("SEPA_EUR", utc(2026, 1, 14, 14, 59)).business_date == date(2026, 1, 14)


def test_internal_book_runs_every_day() -> None:
    window = classify_cutoff("INTERNAL_BOOK", utc(2026, 1, 11, 12, 0))  # Sunday
    assert window.business_date == date(2026, 1, 11)
    assert window.timezone == "UTC"


def test_window_open_and_minutes_to_cutoff() -> None:
    window = classify_cutoff("WIRE_USD", utc(2026, 1, 14, 20, 0))
    assert window.is_open_at(utc(2026, 1, 14, 21, 0))
    assert window.minutes_to_cutoff(utc(2026, 1, 14, 21, 0)) == 30
    assert not window.is_open_at(utc(2026, 1, 14, 21, 30))
    assert window.minutes_to_cutoff(utc(2026, 1, 14, 22, 0)) == -30


def test_current_window_status_closing_soon_and_closed() -> None:
    closing = current_window_status("WIRE_USD", utc(2026, 1, 14, 20, 0))
    assert closing.status == "CLOSING_SOON"
    assert closing.minutes_to_cutoff == 90
    open_status = current_window_status("WIRE_USD", utc(2026, 1, 14, 14, 0))
    assert open_status.status == "OPEN"
    closed = current_window_status("CHAPS_GBP", utc(2026, 1, 14, 17, 0))
    assert closed.status == "CLOSED"
    assert closed.minutes_to_cutoff is None
    assert closed.next_window.business_date == date(2026, 1, 15)


def test_current_window_status_on_weekend_points_to_last_closed_window() -> None:
    status = current_window_status("SEPA_EUR", utc(2026, 1, 10, 12, 0))  # Saturday
    assert status.status == "CLOSED"
    assert status.current_window.business_date == date(2026, 1, 9)
    assert status.next_window.business_date == date(2026, 1, 12)


def test_all_window_statuses_covers_every_rail() -> None:
    statuses = all_window_statuses(utc(2026, 1, 14, 12, 0))
    assert [s.rail for s in statuses] == list(load_cutoff_policies())
