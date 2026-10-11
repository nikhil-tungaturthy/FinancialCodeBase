import * as ToastPrimitive from '@radix-ui/react-toast';
import { AlertTriangle, CheckCircle2, Info, X, XCircle, type LucideIcon } from 'lucide-react';
import { type ReactNode, useCallback, useMemo, useRef, useState } from 'react';

import {
  ToastContext,
  type ToastContextValue,
  type ToastOptions,
  type ToastRecord,
  type ToastVariant,
} from '@/components/ui/toast-context';
import { cn } from '@/lib/cn';

const VARIANT_META: Record<
  ToastVariant,
  { icon: LucideIcon; iconClass: string; barClass: string }
> = {
  default: { icon: Info, iconClass: 'text-navy-700', barClass: 'bg-navy-700' },
  success: { icon: CheckCircle2, iconClass: 'text-green-600', barClass: 'bg-green-600' },
  warning: { icon: AlertTriangle, iconClass: 'text-amber-600', barClass: 'bg-amber-500' },
  danger: { icon: XCircle, iconClass: 'text-red-600', barClass: 'bg-red-600' },
};

function ToastItem({
  record,
  onOpenChange,
}: {
  record: ToastRecord;
  onOpenChange: (open: boolean) => void;
}) {
  const meta = VARIANT_META[record.variant ?? 'default'];
  const Icon = meta.icon;
  return (
    <ToastPrimitive.Root
      open={record.open}
      onOpenChange={onOpenChange}
      duration={record.duration}
      className={cn(
        'relative flex w-full items-start gap-3 overflow-hidden rounded-lg border border-slate-200 bg-white p-4 pr-10 shadow-pop',
        'data-[state=open]:animate-slide-in-right data-[state=closed]:animate-fade-out',
      )}
    >
      <span aria-hidden="true" className={cn('absolute inset-y-0 left-0 w-1', meta.barClass)} />
      <Icon className={cn('mt-0.5 size-4 shrink-0', meta.iconClass)} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <ToastPrimitive.Title className="text-sm font-semibold text-navy-900">
          {record.title}
        </ToastPrimitive.Title>
        {record.description && (
          <ToastPrimitive.Description className="mt-0.5 text-xs leading-relaxed text-slate-600">
            {record.description}
          </ToastPrimitive.Description>
        )}
        {record.action && (
          <ToastPrimitive.Action asChild altText={record.action.label}>
            <button
              type="button"
              onClick={record.action.onClick}
              className="mt-2 text-xs font-medium text-teal-700 hover:underline"
            >
              {record.action.label}
            </button>
          </ToastPrimitive.Action>
        )}
      </div>
      <ToastPrimitive.Close
        aria-label="Dismiss notification"
        className="absolute top-3 right-3 rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-navy-900"
      >
        <X className="size-3.5" aria-hidden="true" />
      </ToastPrimitive.Close>
    </ToastPrimitive.Root>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.map((t) => (t.id === id ? { ...t, open: false } : t)));
  }, []);

  const remove = useCallback((id: string) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((options: ToastOptions) => {
    counter.current += 1;
    const id = `toast-${counter.current}`;
    setToasts((current) => [
      ...current.slice(-4),
      { ...options, id, open: true, duration: options.duration ?? 5000 },
    ]);
    return id;
  }, []);

  const value = useMemo<ToastContextValue>(() => ({ toast, dismiss }), [toast, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="right" label="Notifications">
        {children}
        {toasts.map((record) => (
          <ToastItem
            key={record.id}
            record={record}
            onOpenChange={(open) => {
              if (!open) {
                dismiss(record.id);
                window.setTimeout(() => remove(record.id), 250);
              }
            }}
          />
        ))}
        <ToastPrimitive.Viewport className="fixed right-0 bottom-0 z-[100] flex w-full max-w-sm flex-col gap-2 p-4 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
