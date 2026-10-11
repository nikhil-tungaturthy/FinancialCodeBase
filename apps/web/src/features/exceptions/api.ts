import { apiGet, apiPost } from '@/lib/api-client';
import type {
  AddExceptionNoteRequest,
  AssignExceptionRequest,
  ExceptionActionRequest,
  ExceptionActionResponse,
  ExceptionDetail,
  ExceptionListParams,
  ExceptionQueueItem,
  ExceptionSummary,
  Page,
} from '@/types/api';

export function fetchExceptions(
  params: ExceptionListParams = {},
  signal?: AbortSignal,
): Promise<Page<ExceptionQueueItem>> {
  return apiGet<Page<ExceptionQueueItem>>('/exceptions', {
    query: {
      status: params.status,
      severity: params.severity,
      assigned_to: params.assigned_to,
      queue: params.queue,
      search: params.search,
      sort: params.sort,
      order: params.order,
      page: params.page,
      page_size: params.page_size,
    },
    signal,
  });
}

export function fetchExceptionSummary(signal?: AbortSignal): Promise<ExceptionSummary> {
  return apiGet<ExceptionSummary>('/exceptions/summary', { signal });
}

export function fetchException(
  exceptionRef: string,
  signal?: AbortSignal,
): Promise<ExceptionDetail> {
  return apiGet<ExceptionDetail>(`/exceptions/${encodeURIComponent(exceptionRef)}`, { signal });
}

export function assignException(
  exceptionRef: string,
  body: AssignExceptionRequest,
): Promise<ExceptionDetail> {
  return apiPost<ExceptionDetail>(`/exceptions/${encodeURIComponent(exceptionRef)}/assign`, body);
}

export function addExceptionNote(
  exceptionRef: string,
  body: AddExceptionNoteRequest,
): Promise<ExceptionDetail> {
  return apiPost<ExceptionDetail>(`/exceptions/${encodeURIComponent(exceptionRef)}/notes`, body);
}

export function performExceptionAction(
  exceptionRef: string,
  body: ExceptionActionRequest,
): Promise<ExceptionActionResponse> {
  return apiPost<ExceptionActionResponse>(
    `/exceptions/${encodeURIComponent(exceptionRef)}/actions`,
    body,
  );
}
