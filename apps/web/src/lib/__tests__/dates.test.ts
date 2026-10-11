import { describe, expect, it } from 'vitest';

import {
  formatDurationMinutes,
  formatUtcDateTime,
  formatUtcDateTimeLong,
  minutesBetween,
  toDate,
} from '@/lib/dates';

describe('dates', () => {
  it('formats the canonical UTC display form regardless of host timezone', () => {
    expect(formatUtcDateTime('2026-03-18T18:40:00+00:00')).toBe('18:40 UTC · 18 Mar 2026');
    expect(formatUtcDateTime('2026-03-18T14:40:00-04:00')).toBe('18:40 UTC · 18 Mar 2026');
    expect(formatUtcDateTimeLong('2026-03-18T18:40:00Z')).toBe('18:40 UTC · Wed 18 Mar 2026');
  });

  it('treats date-only strings as UTC midnight', () => {
    expect(toDate('2026-03-18')?.toISOString()).toBe('2026-03-18T00:00:00.000Z');
    expect(toDate('')).toBeNull();
    expect(toDate('not a date')).toBeNull();
  });

  it('computes signed minute differences and compact durations', () => {
    expect(minutesBetween('2026-03-18T18:40:00Z', '2026-03-18T20:30:00Z')).toBe(110);
    expect(minutesBetween('2026-03-18T18:40:00Z', '2026-03-18T18:28:00Z')).toBe(-12);
    expect(formatDurationMinutes(110)).toBe('1h 50m');
    expect(formatDurationMinutes(60)).toBe('1h');
    expect(formatDurationMinutes(3000)).toBe('2d 2h');
    expect(formatDurationMinutes(0)).toBe('0m');
  });
});
