import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';
import {
  formatIsoUtc,
  formatUtcDate,
  formatUtcDateTime,
  formatUtcDateWithWeekday,
  formatUtcTime,
  toDate,
} from '@/lib/dates';

export type DateTimeMode = 'datetime' | 'date' | 'time' | 'date-weekday';

export interface DateTimeProps extends Omit<ComponentPropsWithRef<'time'>, 'children'> {
  value: string | Date | null | undefined;
  mode?: DateTimeMode;
}

/**
 * UTC timestamp display, e.g. `18:40 UTC · 18 Mar 2026`, with the full ISO
 * instant available on hover and in the `dateTime` attribute.
 */
export function DateTime({ value, mode = 'datetime', className, ...props }: DateTimeProps) {
  const date = toDate(value);
  if (!date) {
    return (
      <span className={cn('text-slate-400', className)} aria-label="No date">
        —
      </span>
    );
  }
  const iso = formatIsoUtc(date);
  let text: string;
  switch (mode) {
    case 'date':
      text = formatUtcDate(date);
      break;
    case 'time':
      text = `${formatUtcTime(date)} UTC`;
      break;
    case 'date-weekday':
      text = formatUtcDateWithWeekday(date);
      break;
    default:
      text = formatUtcDateTime(date);
  }
  return (
    <time dateTime={iso} title={iso} className={cn('tnum whitespace-nowrap', className)} {...props}>
      {text}
    </time>
  );
}
