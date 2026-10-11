import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';

export interface TextareaProps extends ComponentPropsWithRef<'textarea'> {
  invalid?: boolean;
}

export function Textarea({ className, invalid = false, rows = 3, ...props }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(
        'w-full rounded-md border bg-white px-3 py-2 text-sm text-slate-800 shadow-sm placeholder:text-slate-400',
        'transition-colors focus:border-teal-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/30',
        'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
        invalid ? 'border-red-600 focus:border-red-600' : 'border-slate-300',
        className,
      )}
      {...props}
    />
  );
}
