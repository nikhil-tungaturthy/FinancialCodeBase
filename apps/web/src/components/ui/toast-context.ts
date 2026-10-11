import { createContext } from 'react';

export type ToastVariant = 'default' | 'success' | 'warning' | 'danger';

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  /** Milliseconds before auto-dismiss. Default 5000; `Infinity` keeps it until dismissed. */
  duration?: number;
  action?: { label: string; onClick: () => void };
}

export interface ToastRecord extends ToastOptions {
  id: string;
  open: boolean;
}

export interface ToastContextValue {
  toast: (options: ToastOptions) => string;
  dismiss: (id: string) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);
