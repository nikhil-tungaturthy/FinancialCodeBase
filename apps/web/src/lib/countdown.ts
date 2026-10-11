import { formatDurationMinutes, minutesBetween, toDate } from '@/lib/dates';
import type { Tone } from '@/types/domain';

export interface CountdownState {
  tone: Tone;
  label: string;
  minutes: number | null;
}

/**
 * Derive the display state for a due-by instant relative to a reference "now"
 * (normally the scenario clock). Overdue → danger, inside the warning window →
 * warning, otherwise neutral.
 */
export function computeCountdown(
  dueBy: string | Date | null | undefined,
  now: string | Date,
  warnWithinMinutes = 120,
  prefix = 'Due in',
): CountdownState {
  const due = toDate(dueBy);
  if (!due) return { tone: 'neutral', label: 'No SLA', minutes: null };
  const minutes = minutesBetween(now, due);
  if (minutes === null) return { tone: 'neutral', label: 'No SLA', minutes: null };
  if (minutes < 0) {
    return { tone: 'danger', label: `Overdue ${formatDurationMinutes(minutes)}`, minutes };
  }
  if (minutes < warnWithinMinutes) {
    return { tone: 'warning', label: `${prefix} ${formatDurationMinutes(minutes)}`, minutes };
  }
  return { tone: 'neutral', label: `${prefix} ${formatDurationMinutes(minutes)}`, minutes };
}
