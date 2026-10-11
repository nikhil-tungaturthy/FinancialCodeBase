import { ArrowRight, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { Skeleton } from '@/components/ui/Skeleton';
import { TONE_ICON_BG_CLASSES, TONE_TEXT_CLASSES } from '@/components/ui/tones';
import { cn } from '@/lib/cn';
import type { Tone } from '@/types/domain';

export interface KpiTileProps {
  label: string;
  value: ReactNode;
  /** Secondary line — a delta, breakdown or qualifier. */
  subtext?: ReactNode;
  /** Colour the subtext (e.g. `danger` for a growing exception count). */
  subtextTone?: Tone;
  icon?: LucideIcon;
  iconTone?: Tone;
  /** Navigates on click and renders a trailing arrow. */
  to?: string;
  linkLabel?: string;
  isLoading?: boolean;
  className?: string;
  testId?: string;
}

export function KpiTile({
  label,
  value,
  subtext,
  subtextTone = 'neutral',
  icon: Icon,
  iconTone = 'navy',
  to,
  linkLabel = 'View',
  isLoading = false,
  className,
  testId,
}: KpiTileProps) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
        {Icon && (
          <span
            aria-hidden="true"
            className={cn(
              'flex size-8 shrink-0 items-center justify-center rounded-md [&_svg]:size-4',
              TONE_ICON_BG_CLASSES[iconTone],
            )}
          >
            <Icon />
          </span>
        )}
      </div>
      <div className="mt-2 min-h-8">
        {isLoading ? (
          <Skeleton className="h-7 w-28" />
        ) : (
          <p className="tnum text-2xl leading-8 font-semibold tracking-tight text-navy-900">
            {value}
          </p>
        )}
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs">
        {isLoading ? (
          <Skeleton className="h-3 w-24" />
        ) : (
          <span className={cn('truncate', TONE_TEXT_CLASSES[subtextTone])}>
            {subtext ?? <>&nbsp;</>}
          </span>
        )}
        {to && !isLoading && (
          <span className="inline-flex shrink-0 items-center gap-0.5 font-medium text-teal-700 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
            {linkLabel}
            <ArrowRight className="size-3" aria-hidden="true" />
          </span>
        )}
      </div>
    </>
  );

  const baseClasses = 'group block rounded-lg border border-slate-200 bg-surface p-4 shadow-card';
  if (to) {
    return (
      <Link
        to={to}
        aria-label={`${label}: ${linkLabel}`}
        data-testid={testId}
        className={cn(
          baseClasses,
          'transition-colors hover:border-teal-600/40 hover:bg-teal-50/30',
          className,
        )}
      >
        {body}
      </Link>
    );
  }
  return (
    <div className={cn(baseClasses, className)} data-testid={testId}>
      {body}
    </div>
  );
}
