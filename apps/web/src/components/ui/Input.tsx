import type { ComponentPropsWithRef, ReactNode } from 'react';

import { cn } from '@/lib/cn';

export interface InputProps extends ComponentPropsWithRef<'input'> {
  invalid?: boolean;
  leadingIcon?: ReactNode;
  inputSize?: 'sm' | 'md';
}

export function Input({
  className,
  invalid = false,
  leadingIcon,
  inputSize = 'md',
  type = 'text',
  ...props
}: InputProps) {
  const control = (
    <input
      type={type}
      aria-invalid={invalid || undefined}
      className={cn(
        'w-full rounded-md border bg-white text-slate-800 shadow-sm placeholder:text-slate-400',
        'transition-colors focus:border-teal-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/30',
        'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
        inputSize === 'sm' ? 'h-8 px-2.5 text-xs' : 'h-9 px-3 text-sm',
        leadingIcon && (inputSize === 'sm' ? 'pl-8' : 'pl-9'),
        invalid ? 'border-red-600 focus:border-red-600' : 'border-slate-300',
        className,
      )}
      {...props}
    />
  );
  if (!leadingIcon) return control;
  return (
    <div className="relative">
      <span
        aria-hidden="true"
        className={cn(
          'pointer-events-none absolute top-1/2 -translate-y-1/2 text-slate-400 [&_svg]:size-4',
          inputSize === 'sm' ? 'left-2.5' : 'left-3',
        )}
      >
        {leadingIcon}
      </span>
      {control}
    </div>
  );
}
