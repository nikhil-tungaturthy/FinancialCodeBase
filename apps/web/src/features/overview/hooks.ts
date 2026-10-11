import { useQuery } from '@tanstack/react-query';

import { fetchOverview, type OverviewParams } from '@/features/overview/api';

export const overviewKeys = {
  all: ['overview'] as const,
  detail: (params: OverviewParams) => [...overviewKeys.all, params] as const,
};

export function useOverview(params: OverviewParams = {}) {
  return useQuery({
    queryKey: overviewKeys.detail(params),
    queryFn: ({ signal }) => fetchOverview(params, signal),
  });
}
