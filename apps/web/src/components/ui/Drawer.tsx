import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { ComponentPropsWithRef } from 'react';

import { DialogOverlay } from '@/components/ui/Dialog';
import { cn } from '@/lib/cn';

export const Drawer = DialogPrimitive.Root;
export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;

export interface DrawerContentProps extends ComponentPropsWithRef<typeof DialogPrimitive.Content> {
  side?: 'right' | 'left';
  /** Tailwind width class, default `max-w-xl`. */
  widthClassName?: string;
  hideClose?: boolean;
}

/** Side panel built on Radix Dialog — modal, focus-trapped, dismissable with Escape. */
export function DrawerContent({
  className,
  children,
  side = 'right',
  widthClassName = 'max-w-xl',
  hideClose = false,
  ...props
}: DrawerContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        className={cn(
          'fixed inset-y-0 z-50 flex h-full w-full flex-col border-slate-200 bg-white shadow-pop focus:outline-none',
          side === 'right' ? 'right-0 border-l' : 'left-0 border-r',
          side === 'right'
            ? 'data-[state=open]:animate-slide-in-right data-[state=closed]:animate-slide-out-right'
            : 'data-[state=open]:animate-slide-in-left data-[state=closed]:animate-slide-out-left',
          widthClassName,
          className,
        )}
        {...props}
      >
        {children}
        {!hideClose && (
          <DialogPrimitive.Close
            className="absolute top-3.5 right-4 rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-navy-900"
            aria-label="Close panel"
          >
            <X className="size-4" aria-hidden="true" />
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DrawerHeader({ className, ...props }: ComponentPropsWithRef<'div'>) {
  return (
    <div
      className={cn('flex flex-col gap-1 border-b border-slate-200 px-6 py-4 pr-12', className)}
      {...props}
    />
  );
}

export function DrawerTitle({
  className,
  ...props
}: ComponentPropsWithRef<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      className={cn('text-base font-semibold text-navy-900', className)}
      {...props}
    />
  );
}

export function DrawerDescription({
  className,
  ...props
}: ComponentPropsWithRef<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description className={cn('text-xs text-slate-500', className)} {...props} />
  );
}

export function DrawerBody({ className, ...props }: ComponentPropsWithRef<'div'>) {
  return (
    <div className={cn('flex-1 overflow-y-auto px-6 py-5 scrollbar-thin', className)} {...props} />
  );
}

export function DrawerFooter({ className, ...props }: ComponentPropsWithRef<'div'>) {
  return (
    <div
      className={cn(
        'flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-3',
        className,
      )}
      {...props}
    />
  );
}
