"""Business-day calendar helpers for settlement rails.

Each rail carries its own operating calendar (weekday set plus explicit holidays),
because cutoff schedules differ by rail and jurisdiction. All functions are pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

WEEKDAY_CODES: tuple[str, ...] = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


@dataclass(frozen=True, slots=True)
class BusinessCalendar:
    """Operating calendar for a rail: which weekdays operate and which dates are holidays."""

    business_weekdays: frozenset[int]
    holidays: frozenset[date] = field(default_factory=frozenset)

    @classmethod
    def from_codes(cls, weekday_codes: list[str], holidays: list[str]) -> BusinessCalendar:
        weekdays = frozenset(WEEKDAY_CODES.index(code.upper()) for code in weekday_codes)
        return cls(
            business_weekdays=weekdays,
            holidays=frozenset(date.fromisoformat(value) for value in holidays),
        )

    def is_business_day(self, day: date) -> bool:
        return day.weekday() in self.business_weekdays and day not in self.holidays

    def next_business_day(self, day: date, *, inclusive: bool = False) -> date:
        """Return the first business day on/after ``day`` (``inclusive``) or strictly after it."""
        candidate = day if inclusive else day + timedelta(days=1)
        # Bounded loop: a calendar with no business weekdays is a configuration error.
        for _ in range(0, 400):
            if self.is_business_day(candidate):
                return candidate
            candidate += timedelta(days=1)
        msg = "Calendar has no business days within 400 days; check rail configuration"
        raise ValueError(msg)

    def add_business_days(self, day: date, offset: int) -> date:
        """Advance ``day`` by ``offset`` business days (0 returns ``day`` unchanged)."""
        if offset < 0:
            msg = "Negative business-day offsets are not supported"
            raise ValueError(msg)
        current = day
        for _ in range(offset):
            current = self.next_business_day(current)
        return current
