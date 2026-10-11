import { apiGet } from '@/lib/api-client';
import type { AuditEvent, AuditListParams, Page } from '@/types/api';

export function fetchAuditEvents(
  params: AuditListParams = {},
  signal?: AbortSignal,
): Promise<Page<AuditEvent>> {
  return apiGet<Page<AuditEvent>>('/audit', {
    query: {
      entity_type: params.entity_type,
      entity_ref: params.entity_ref,
      action: params.action,
      actor: params.actor,
      correlation_id: params.correlation_id,
      date_from: params.date_from,
      date_to: params.date_to,
      search: params.search,
      page: params.page,
      page_size: params.page_size,
    },
    signal,
  });
}

export function fetchAuditActions(signal?: AbortSignal): Promise<string[]> {
  return apiGet<string[] | { items: string[] }>('/audit/actions', { signal }).then((payload) =>
    Array.isArray(payload) ? payload : payload.items,
  );
}

export function fetchAuditEvent(eventId: string, signal?: AbortSignal): Promise<AuditEvent> {
  return apiGet<AuditEvent>(`/audit/${encodeURIComponent(eventId)}`, { signal });
}
