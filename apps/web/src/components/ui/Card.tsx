import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';

export function Card({ className, ...props }: ComponentPropsWithRef<'section'>) {
  return (
    <section
      className={cn(
        'rounded-lg border border-slate-200 bg-surface text-slate-800 shadow-card',
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: ComponentPropsWithRef<'header'>) {
  return (
    <header
      className={cn(
        'flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-3.5',
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({ className, children, ...props }: ComponentPropsWithRef<'h2'>) {
  return (
    <h2 className={cn('text-sm font-semibold text-navy-900', className)} {...props}>
      {children}
    </h2>
  );
}

export function CardDescription({ className, ...props }: ComponentPropsWithRef<'p'>) {
  return <p className={cn('mt-0.5 text-xs text-slate-500', className)} {...props} />;
}

export function CardContent({ className, ...props }: ComponentPropsWithRef<'div'>) {
  return <div className={cn('px-5 py-4', className)} {...props} />;
}

export function CardFooter({ className, ...props }: ComponentPropsWithRef<'footer'>) {
  return (
    <footer
      className={cn(
        'flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3',
        className,
      )}
      {...props}
    />
  );
}
