import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';

export function Skeleton({ className, ...props }: ComponentPropsWithRef<'div'>) {
  return (
    <div
      aria-hidden="true"
      className={cn('animate-pulse rounded-md bg-slate-200/80', className)}
      {...props}
    />
  );
}

/** A block of text-like skeleton lines. */
export function SkeletonLines({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)} aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton
          key={index}
          className="h-3.5"
          style={{ width: `${index === lines - 1 ? 55 : 100 - index * 8}%` }}
        />
      ))}
    </div>
  );
}
