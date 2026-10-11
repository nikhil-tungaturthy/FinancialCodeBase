import { differenceInMinutes, isValid, parseISO } from 'date-fns';

/**
 * All operational timestamps are displayed in UTC (SPEC §0.2, display_timezone
 * "UTC"). We rely on `Intl.DateTimeFormat` with an explicit `timeZone` so the
 * output is independent of the viewer's machine, and on date-fns for arithmetic.
 */

const UTC_TIME = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const UTC_TIME_SECONDS = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

const UTC_DATE = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

const UTC_DATE_WEEKDAY = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

const UTC_DAY_MONTH = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'UTC',
  day: 'numeric',
  month: 'short',
});

export type DateInput = string | Date | null | undefined;

/** Parse an ISO datetime or `YYYY-MM-DD` date (treated as UTC midnight). Returns null when invalid. */
export function toDate(input: DateInput): Date | null {
  if (!input) return null;
  if (input instanceof Date) return isValid(input) ? input : null;
  const trimmed = input.trim();
  if (!trimmed) return null;
  const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(trimmed);
  const parsed = parseISO(isDateOnly ? `${trimmed}T00:00:00Z` : trimmed);
  return isValid(parsed) ? parsed : null;
}

/** `18:40` */
export function formatUtcTime(input: DateInput, withSeconds = false): string {
  const date = toDate(input);
  if (!date) return '—';
  return (withSeconds ? UTC_TIME_SECONDS : UTC_TIME).format(date);
}

/** `18 Mar 2026` */
export function formatUtcDate(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '—';
  return UTC_DATE.format(date);
}

/** `Wed 18 Mar 2026` */
export function formatUtcDateWithWeekday(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '—';
  return UTC_DATE_WEEKDAY.format(date).replace(',', '');
}

/** `18 Mar` */
export function formatUtcDayMonth(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '—';
  return UTC_DAY_MONTH.format(date);
}

/** `18:40 UTC · 18 Mar 2026` — the canonical display form for timestamps. */
export function formatUtcDateTime(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '—';
  return `${UTC_TIME.format(date)} UTC · ${UTC_DATE.format(date)}`;
}

/** `Scenario time 18:40 UTC · Wed 18 Mar 2026` without the prefix. */
export function formatUtcDateTimeLong(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '—';
  return `${UTC_TIME.format(date)} UTC · ${formatUtcDateWithWeekday(date)}`;
}

/** Full ISO-8601 in UTC with `Z`, used for `title` tooltips. */
export function formatIsoUtc(input: DateInput): string {
  const date = toDate(input);
  if (!date) return '';
  return date.toISOString();
}

/** Signed whole minutes from `from` to `to` (positive when `to` is later). */
export function minutesBetween(from: DateInput, to: DateInput): number | null {
  const a = toDate(from);
  const b = toDate(to);
  if (!a || !b) return null;
  return differenceInMinutes(b, a);
}

/** `1h 50m`, `12m`, `2d 3h`. Always non-negative; the caller decides the sign wording. */
export function formatDurationMinutes(totalMinutes: number): string {
  const minutes = Math.abs(Math.round(totalMinutes));
  if (minutes < 1) return '0m';
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const mins = minutes % 60;
  if (days > 0) return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  if (hours > 0) return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  return `${mins}m`;
}

/** Relative age label against a reference "now" (scenario clock): `12m ago`, `3h ago`, `2d ago`. */
export function formatAge(input: DateInput, now: DateInput): string {
  const minutes = minutesBetween(input, now);
  if (minutes === null) return '—';
  if (minutes < 1) return 'just now';
  return `${formatDurationMinutes(minutes)} ago`;
}

/** Local time label for a rail cutoff: `16:30 America/New_York`. */
export function formatCutoffLocal(
  cutoffLocal: string | null | undefined,
  timezone: string | null | undefined,
): string {
  if (!cutoffLocal) return '—';
  return timezone ? `${cutoffLocal} ${timezone}` : cutoffLocal;
}
