import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
  /** Tailwind grid-cols template applied from `lg` up. */
  template?: string;
  className?: string;
  leftClassName?: string;
  rightClassName?: string;
  leftLabel?: string;
  rightLabel?: string;
}

/**
 * Fixed two-column layout (queue + detail) that stacks below 1024px. Each side
 * scrolls independently when the pane is given a bounded height by its parent.
 */
export function SplitPane({
  left,
  right,
  template = 'lg:grid-cols-[minmax(380px,5fr)_minmax(440px,7fr)]',
  className,
  leftClassName,
  rightClassName,
  leftLabel = 'List',
  rightLabel = 'Detail',
}: SplitPaneProps) {
  return (
    <div className={cn('grid min-h-0 grid-cols-1 gap-4', template, className)}>
      <section
        aria-label={leftLabel}
        className={cn('flex min-h-0 min-w-0 flex-col', leftClassName)}
      >
        {left}
      </section>
      <section
        aria-label={rightLabel}
        className={cn('flex min-h-0 min-w-0 flex-col', rightClassName)}
      >
        {right}
      </section>
    </div>
  );
}
