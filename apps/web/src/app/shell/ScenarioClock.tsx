import { Clock3 } from 'lucide-react';

import { Skeleton } from '@/components/ui/Skeleton';
import { Tooltip } from '@/components/ui/Tooltip';
import { formatUtcDateTimeLong } from '@/lib/dates';
import { useScenario } from '@/lib/scenario';

/**
 * Displays the platform's fixed scenario instant, e.g.
 * "Scenario time 18:40 UTC · Wed 18 Mar 2026". Every age, SLA countdown and
 * cutoff status in the UI is computed against this clock, not the wall clock.
 */
export function ScenarioClock() {
  const { data, isPending, isError } = useScenario();

  if (isPending) {
    return <Skeleton className="h-6 w-56" data-testid="scenario-clock-loading" />;
  }

  if (isError || !data) {
    return (
      <span className="text-xs text-slate-400" data-testid="scenario-clock">
        Scenario clock unavailable
      </span>
    );
  }

  const label = formatUtcDateTimeLong(data.scenario_now);

  return (
    <Tooltip
      content={
        <span>
          The environment runs on a fixed scenario clock ({data.business_day_label}). All ages, SLA
          countdowns and settlement cutoffs are computed from this instant rather than the real
          time, so the demo is reproducible. Seed {data.seed_version}.
        </span>
      }
      side="bottom"
    >
      <button
        type="button"
        data-testid="scenario-clock"
        className="tnum inline-flex h-8 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 text-xs text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
      >
        <Clock3 className="size-3.5 text-teal-700" aria-hidden="true" />
        <span>
          <span className="text-slate-500">Scenario time</span>{' '}
          <span className="font-medium text-navy-900">{label}</span>
        </span>
      </button>
    </Tooltip>
  );
}
