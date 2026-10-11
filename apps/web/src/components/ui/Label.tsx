import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';

export interface LabelProps extends ComponentPropsWithRef<'label'> {
  required?: boolean;
}

export function Label({ className, required, children, ...props }: LabelProps) {
  return (
    <label className={cn('mb-1.5 block text-xs font-medium text-slate-600', className)} {...props}>
      {children}
      {required && (
        <span aria-hidden="true" className="ml-0.5 text-red-600">
          *
        </span>
      )}
    </label>
  );
}
