import type { ComponentPropsWithRef } from 'react';
import { Link } from 'react-router';

import { cn } from '@/lib/cn';

export interface RefLinkProps extends Omit<ComponentPropsWithRef<typeof Link>, 'to'> {
  to: string;
  /** Render as plain text when the target cannot be resolved. */
  disabled?: boolean;
}

/**
 * Monospace reference link (`MGB-PAY-1042`) for table cells. Click events do
 * not bubble so that a row-level `onRowClick` is not triggered twice.
 */
export function RefLink({
  to,
  className,
  disabled = false,
  children,
  onClick,
  ...props
}: RefLinkProps) {
  if (disabled) {
    return <span className={cn('font-mono text-xs text-slate-700', className)}>{children}</span>;
  }
  return (
    <Link
      to={to}
      className={cn(
        'rounded-sm font-mono text-xs font-medium text-teal-700 underline-offset-2 hover:underline',
        className,
      )}
      onClick={(event) => {
        event.stopPropagation();
        onClick?.(event);
      }}
      {...props}
    >
      {children}
    </Link>
  );
}
