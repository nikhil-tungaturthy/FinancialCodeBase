import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchAuditActions, fetchAuditEvent, fetchAuditEvents } from '@/features/audit/api';
import type { AuditListParams } from '@/types/api';

export const auditKeys = {
  all: ['audit'] as const,
  lists: () => [...auditKeys.all, 'list'] as const,
  list: (params: AuditListParams) => [...auditKeys.lists(), params] as const,
  actions: () => [...auditKeys.all, 'actions'] as const,
  detail: (eventId: string) => [...auditKeys.all, 'detail', eventId] as const,
};

export function useAuditEvents(params: AuditListParams) {
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: ({ signal }) => fetchAuditEvents(params, signal),
    placeholderData: keepPreviousData,
  });
}

export function useAuditActions() {
  return useQuery({
    queryKey: auditKeys.actions(),
    queryFn: ({ signal }) => fetchAuditActions(signal),
    staleTime: Infinity,
  });
}

export function useAuditEvent(eventId: string | undefined) {
  return useQuery({
    queryKey: auditKeys.detail(eventId ?? ''),
    queryFn: ({ signal }) => fetchAuditEvent(eventId!, signal),
    enabled: Boolean(eventId),
  });
}
