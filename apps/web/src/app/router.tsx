import { createBrowserRouter, type RouteObject } from 'react-router';

import type { RouteHandle } from '@/app/navigation';
import { AppShell } from '@/app/shell/AppShell';

const handle = (title: RouteHandle['title']): RouteHandle => ({ title });

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    lazy: {
      ErrorBoundary: async () => (await import('@/app/pages/RouteErrorPage')).default,
    },
    children: [
      {
        index: true,
        handle: handle('Overview'),
        lazy: {
          Component: async () => (await import('@/features/overview/pages/OverviewPage')).default,
        },
      },
      {
        path: 'payments',
        handle: handle('Payments'),
        children: [
          {
            index: true,
            lazy: {
              Component: async () =>
                (await import('@/features/payments/pages/PaymentsPage')).default,
            },
          },
          {
            path: ':paymentRef',
            handle: handle((params) => params.paymentRef ?? 'Payment'),
            lazy: {
              Component: async () =>
                (await import('@/features/payments/pages/PaymentDetailPage')).default,
            },
          },
        ],
      },
      {
        path: 'exceptions',
        handle: handle('Exceptions'),
        children: [
          {
            index: true,
            lazy: {
              Component: async () =>
                (await import('@/features/exceptions/pages/ExceptionsPage')).default,
            },
          },
          {
            path: ':exceptionRef',
            handle: handle((params) => params.exceptionRef ?? 'Exception'),
            lazy: {
              Component: async () =>
                (await import('@/features/exceptions/pages/ExceptionsPage')).default,
            },
          },
        ],
      },
      {
        path: 'settlement',
        handle: handle('Settlement'),
        children: [
          {
            index: true,
            lazy: {
              Component: async () =>
                (await import('@/features/settlement/pages/SettlementPage')).default,
            },
          },
          {
            path: 'batches/:batchRef',
            handle: handle((params) => params.batchRef ?? 'Settlement batch'),
            lazy: {
              Component: async () =>
                (await import('@/features/settlement/pages/BatchDetailPage')).default,
            },
          },
        ],
      },
      {
        path: 'approvals',
        handle: handle('Approvals'),
        children: [
          {
            index: true,
            lazy: {
              Component: async () =>
                (await import('@/features/approvals/pages/ApprovalsPage')).default,
            },
          },
          {
            path: ':approvalRef',
            handle: handle((params) => params.approvalRef ?? 'Approval'),
            lazy: {
              Component: async () =>
                (await import('@/features/approvals/pages/ApprovalsPage')).default,
            },
          },
        ],
      },
      {
        path: 'audit',
        handle: handle('Audit'),
        lazy: { Component: async () => (await import('@/features/audit/pages/AuditPage')).default },
      },
      {
        path: 'policies',
        handle: handle('Policies'),
        lazy: {
          Component: async () => (await import('@/features/policies/pages/PoliciesPage')).default,
        },
      },
      {
        path: '*',
        handle: handle('Not found'),
        lazy: { Component: async () => (await import('@/app/pages/NotFoundPage')).default },
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
