import { AlarmClock, Clock } from 'lucide-react';

import { Badge, type BadgeProps } from '@/components/ui/Badge';
import { computeCountdown } from '@/lib/countdown';
import { formatIsoUtc } from '@/lib/dates';
import { useScenarioNow } from '@/lib/scenario';

export interface CountdownChipProps extends Omit<BadgeProps, 'tone' | 'children'> {
  /** The SLA / cutoff instant. `null` renders a neutral "No SLA" chip. */
  dueBy: string | Date | null | undefined;
  /** Reference instant. Defaults to the scenario clock from `/meta/scenario`. */
  now?: string | Date;
  /** Minutes before `dueBy` at which the chip turns amber. */
  warnWithinMinutes?: number;
  /** Wording for the time-remaining state. */
  prefix?: string;
}

export function CountdownChip({
  dueBy,
  now,
  warnWithinMinutes = 120,
  prefix,
  size = 'md',
  ...props
}: CountdownChipProps) {
  const scenarioNow = useScenarioNow();
  const reference = now ?? scenarioNow;
  const state = computeCountdown(dueBy, reference, warnWithinMinutes, prefix);
  const Icon = state.tone === 'danger' ? AlarmClock : Clock;
  const dueIso = formatIsoUtc(dueBy);
  return (
    <Badge
      tone={state.tone}
      size={size}
      title={dueIso ? `Due by ${dueIso}` : undefined}
      data-countdown={state.tone}
      {...props}
    >
      <Icon aria-hidden="true" className="-ml-0.5 size-3.5 shrink-0" />
      <span className="tnum">{state.label}</span>
    </Badge>
  );
}
