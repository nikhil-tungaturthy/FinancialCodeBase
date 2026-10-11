import { apiGet } from '@/lib/api-client';
import type { Overview } from '@/types/api';

export interface OverviewParams {
  /** `YYYY-MM-DD`; defaults to the scenario date server-side. */
  date?: string;
}

export function fetchOverview(
  params: OverviewParams = {},
  signal?: AbortSignal,
): Promise<Overview> {
  return apiGet<Overview>('/overview', { query: { date: params.date }, signal });
}
