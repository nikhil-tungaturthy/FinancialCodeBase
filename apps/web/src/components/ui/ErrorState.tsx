import { AlertOctagon, RotateCw } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { ApiError, describeError } from '@/lib/api-client';
import { cn } from '@/lib/cn';

export interface ErrorStateProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

export function ErrorState({
  error,
  title,
  onRetry,
  retrying = false,
  className,
  size = 'md',
}: ErrorStateProps) {
  const described = describeError(error);
  const correlationId = error instanceof ApiError ? error.correlationId : null;
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        size === 'sm' ? 'px-4 py-8' : 'px-6 py-14',
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'flex items-center justify-center rounded-full bg-red-100 text-red-600',
          size === 'sm' ? 'size-9 [&_svg]:size-4' : 'size-12 [&_svg]:size-5',
        )}
      >
        <AlertOctagon />
      </span>
      <h3
        className={cn('mt-3 font-semibold text-navy-900', size === 'sm' ? 'text-sm' : 'text-base')}
      >
        {title ?? described.title}
      </h3>
      <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-500">{described.detail}</p>
      {correlationId && (
        <p className="mt-2 font-mono text-[11px] text-slate-400">Correlation {correlationId}</p>
      )}
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={onRetry}
          loading={retrying}
          loadingLabel="Retrying…"
        >
          <RotateCw aria-hidden="true" />
          Retry
        </Button>
      )}
    </div>
  );
}
