import { Inbox, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  size = 'md',
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        size === 'sm' ? 'px-4 py-8' : 'px-6 py-14',
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'flex items-center justify-center rounded-full bg-slate-100 text-slate-500',
          size === 'sm' ? 'size-9 [&_svg]:size-4' : 'size-12 [&_svg]:size-5',
        )}
      >
        <Icon />
      </span>
      <h3
        className={cn('mt-3 font-semibold text-navy-900', size === 'sm' ? 'text-sm' : 'text-base')}
      >
        {title}
      </h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
