import type { ComponentPropsWithRef } from 'react';

import { TONE_BADGE_CLASSES, TONE_DOT_CLASSES } from '@/components/ui/tones';
import { cn } from '@/lib/cn';
import type { Tone } from '@/types/domain';

export interface BadgeProps extends ComponentPropsWithRef<'span'> {
  tone?: Tone;
  size?: 'sm' | 'md';
  /** Leading status dot. */
  dot?: boolean;
  /** Uppercase, letter-spaced label (used for severities and codes). */
  uppercase?: boolean;
}

export function Badge({
  tone = 'neutral',
  size = 'md',
  dot = false,
  uppercase = false,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full items-center gap-1.5 rounded-full font-medium whitespace-nowrap ring-1 ring-inset',
        size === 'sm' ? 'h-5 px-2 text-[11px] leading-none' : 'h-6 px-2.5 text-xs leading-none',
        uppercase && 'tracking-wide uppercase',
        TONE_BADGE_CLASSES[tone],
        className,
      )}
      {...props}
    >
      {dot && (
        <span
          aria-hidden="true"
          className={cn('size-1.5 shrink-0 rounded-full', TONE_DOT_CLASSES[tone])}
        />
      )}
      {typeof children === 'string' ? <span className="truncate">{children}</span> : children}
    </span>
  );
}
