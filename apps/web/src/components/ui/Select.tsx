import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown } from 'lucide-react';
import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';

export const Select = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;

export interface SelectTriggerProps extends ComponentPropsWithRef<typeof SelectPrimitive.Trigger> {
  size?: 'sm' | 'md';
  invalid?: boolean;
}

export function SelectTrigger({
  className,
  children,
  size = 'md',
  invalid = false,
  ...props
}: SelectTriggerProps) {
  return (
    <SelectPrimitive.Trigger
      aria-invalid={invalid || undefined}
      className={cn(
        'flex w-full items-center justify-between gap-2 rounded-md border bg-white text-left text-slate-800 shadow-sm',
        'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/30 data-[placeholder]:text-slate-400',
        'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
        size === 'sm' ? 'h-8 px-2.5 text-xs' : 'h-9 px-3 text-sm',
        invalid ? 'border-red-600' : 'border-slate-300 hover:border-slate-400',
        className,
      )}
      {...props}
    >
      <span className="truncate">{children}</span>
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="size-4 shrink-0 text-slate-400" aria-hidden="true" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

export function SelectContent({
  className,
  children,
  position = 'popper',
  ...props
}: ComponentPropsWithRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        sideOffset={4}
        className={cn(
          'z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-slate-200 bg-white shadow-pop',
          'data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectLabel({
  className,
  ...props
}: ComponentPropsWithRef<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      className={cn(
        'px-2 py-1.5 text-[11px] font-semibold tracking-wide text-slate-500 uppercase',
        className,
      )}
      {...props}
    />
  );
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentPropsWithRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex cursor-default items-center rounded-sm py-1.5 pr-8 pl-2 text-sm text-slate-800 outline-none select-none',
        'data-[highlighted]:bg-slate-100 data-[highlighted]:text-navy-900 data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator className="absolute right-2 inline-flex items-center">
        <Check className="size-4 text-teal-700" aria-hidden="true" />
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  );
}

export function SelectSeparator({
  className,
  ...props
}: ComponentPropsWithRef<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator className={cn('my-1 h-px bg-slate-100', className)} {...props} />
  );
}
