import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface KeyValueItem {
  label: ReactNode;
  value: ReactNode;
  /** Render the value in monospace (identifiers, hashes). */
  mono?: boolean;
  /** Span the full row in multi-column layouts. */
  fullWidth?: boolean;
  /** Supplementary text under the value. */
  hint?: ReactNode;
}

export interface KeyValueListProps {
  items: ReadonlyArray<KeyValueItem>;
  columns?: 1 | 2 | 3;
  /** Layout: `stacked` puts the label above the value; `inline` places them side by side. */
  layout?: 'stacked' | 'inline';
  className?: string;
  'aria-label'?: string;
}

const COLUMN_CLASSES = { 1: 'sm:grid-cols-1', 2: 'sm:grid-cols-2', 3: 'sm:grid-cols-3' } as const;

export function KeyValueList({
  items,
  columns = 2,
  layout = 'stacked',
  className,
  'aria-label': ariaLabel,
}: KeyValueListProps) {
  return (
    <dl
      aria-label={ariaLabel}
      className={cn(
        'grid grid-cols-1 gap-x-6',
        layout === 'stacked' ? 'gap-y-4' : 'gap-y-2',
        COLUMN_CLASSES[columns],
        className,
      )}
    >
      {items.map((item, index) => (
        <div
          key={index}
          className={cn(
            'min-w-0',
            layout === 'inline' &&
              'flex items-baseline justify-between gap-4 border-b border-slate-100 py-1.5 last:border-b-0',
            item.fullWidth && 'sm:col-span-full',
          )}
        >
          <dt
            className={cn(
              'text-[11px] font-medium tracking-wide text-slate-500 uppercase',
              layout === 'inline' && 'shrink-0',
            )}
          >
            {item.label}
          </dt>
          <dd
            className={cn(
              'text-13 text-slate-800',
              layout === 'stacked' ? 'mt-0.5' : 'text-right',
              item.mono && 'font-mono text-xs',
              'break-words',
            )}
          >
            {item.value === null || item.value === undefined || item.value === '' ? (
              <span className="text-slate-400">—</span>
            ) : (
              item.value
            )}
            {item.hint && (
              <div className="mt-0.5 font-sans text-xs text-slate-500">{item.hint}</div>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
