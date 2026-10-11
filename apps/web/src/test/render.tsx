import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter, type MemoryRouterProps } from 'react-router';

import { ToastProvider } from '@/components/ui/Toast';
import { TooltipProvider } from '@/components/ui/Tooltip';

export interface AppRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial history entries for the in-memory router. */
  initialEntries?: MemoryRouterProps['initialEntries'];
  queryClient?: QueryClient;
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

/** Render with the same providers as the app, backed by a MemoryRouter. */
export function renderWithProviders(
  ui: ReactElement,
  options: AppRenderOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const { initialEntries = ['/'], queryClient = createTestQueryClient(), ...rest } = options;

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={0}>
          <ToastProvider>
            <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
          </ToastProvider>
        </TooltipProvider>
      </QueryClientProvider>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...rest }), queryClient };
}
