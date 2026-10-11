import type { ReactNode } from 'react';

import { ErrorState } from '@/components/ui/ErrorState';

export interface QueryBoundaryProps {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
  isRefetching?: boolean;
  pending: ReactNode;
  children: ReactNode;
  errorTitle?: string;
}

/** Standard pending / error / ready switch for data-driven sections. */
export function QueryBoundary({
  isPending,
  isError,
  error,
  refetch,
  isRefetching = false,
  pending,
  children,
  errorTitle,
}: QueryBoundaryProps) {
  if (isPending) return <>{pending}</>;
  if (isError) {
    return (
      <ErrorState error={error} title={errorTitle} onRetry={refetch} retrying={isRefetching} />
    );
  }
  return <>{children}</>;
}
