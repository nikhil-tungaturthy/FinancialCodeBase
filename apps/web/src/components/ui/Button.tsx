import { Slot } from '@radix-ui/react-slot';
import { type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import type { ComponentPropsWithRef } from 'react';

import { buttonVariants } from '@/components/ui/button-variants';
import { cn } from '@/lib/cn';

export interface ButtonProps
  extends ComponentPropsWithRef<'button'>, VariantProps<typeof buttonVariants> {
  /** Render the child element (e.g. a router `Link`) with button styling. */
  asChild?: boolean;
  /** Shows a spinner, sets `aria-busy` and disables interaction. */
  loading?: boolean;
  /** Accessible label for the loading state. */
  loadingLabel?: string;
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  loadingLabel = 'Working…',
  disabled,
  children,
  type,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : 'button';
  const isDisabled = disabled || loading;
  return (
    <Comp
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      aria-disabled={isDisabled || undefined}
      type={asChild ? undefined : (type ?? 'button')}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="animate-spin" aria-hidden="true" />
          <span className="sr-only">{loadingLabel}</span>
          {children}
        </>
      ) : (
        children
      )}
    </Comp>
  );
}
