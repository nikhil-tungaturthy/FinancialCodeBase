import { apiGet, apiPost } from '@/lib/api-client';
import type {
  BatchDetail,
  BatchListParams,
  BatchSummary,
  LedgerEntry,
  LedgerListParams,
  Page,
  ReconciliationResult,
  ReconciliationSummary,
  SettlementWindow,
} from '@/types/api';

export function fetchBatches(
  params: BatchListParams = {},
  signal?: AbortSignal,
): Promise<Page<BatchSummary>> {
  return apiGet<Page<BatchSummary>>('/settlement/batches', {
    query: {
      status: params.status,
      rail: params.rail,
      value_date: params.value_date,
      page: params.page,
      page_size: params.page_size,
    },
    signal,
  });
}

export function fetchBatch(batchRef: string, signal?: AbortSignal): Promise<BatchDetail> {
  return apiGet<BatchDetail>(`/settlement/batches/${encodeURIComponent(batchRef)}`, { signal });
}

/** Runs baseline reconciliation for a SETTLED / DISCREPANCY / RECONCILED batch (ANALYST+). */
export function reconcileBatch(batchRef: string): Promise<ReconciliationResult> {
  return apiPost<ReconciliationResult>(
    `/settlement/batches/${encodeURIComponent(batchRef)}/reconcile`,
  );
}

export function fetchSettlementWindows(signal?: AbortSignal): Promise<SettlementWindow[]> {
  return apiGet<SettlementWindow[] | { items?: SettlementWindow[]; windows?: SettlementWindow[] }>(
    '/settlement/windows',
    { signal },
  ).then((payload) => {
    if (Array.isArray(payload)) return payload;
    return payload.windows ?? payload.items ?? [];
  });
}

export function fetchReconciliationSummary(signal?: AbortSignal): Promise<ReconciliationSummary> {
  return apiGet<ReconciliationSummary>('/reconciliation/summary', { signal });
}

export function fetchLedgerEntries(
  params: LedgerListParams = {},
  signal?: AbortSignal,
): Promise<Page<LedgerEntry>> {
  return apiGet<Page<LedgerEntry>>('/ledger/entries', {
    query: {
      payment_ref: params.payment_ref,
      batch_ref: params.batch_ref,
      journal_ref: params.journal_ref,
      page: params.page,
      page_size: params.page_size,
    },
    signal,
  });
}
