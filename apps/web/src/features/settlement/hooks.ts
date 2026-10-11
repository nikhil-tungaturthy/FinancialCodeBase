import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  fetchBatch,
  fetchBatches,
  fetchLedgerEntries,
  fetchReconciliationSummary,
  fetchSettlementWindows,
  reconcileBatch,
} from '@/features/settlement/api';
import type { BatchListParams, LedgerListParams } from '@/types/api';

export const settlementKeys = {
  all: ['settlement'] as const,
  batches: () => [...settlementKeys.all, 'batches'] as const,
  batchList: (params: BatchListParams) => [...settlementKeys.batches(), 'list', params] as const,
  batchDetail: (batchRef: string) => [...settlementKeys.batches(), 'detail', batchRef] as const,
  windows: () => [...settlementKeys.all, 'windows'] as const,
  reconciliationSummary: () => [...settlementKeys.all, 'reconciliation-summary'] as const,
  ledger: (params: LedgerListParams) => [...settlementKeys.all, 'ledger', params] as const,
};

export function useBatches(params: BatchListParams) {
  return useQuery({
    queryKey: settlementKeys.batchList(params),
    queryFn: ({ signal }) => fetchBatches(params, signal),
    placeholderData: keepPreviousData,
  });
}

export function useBatch(batchRef: string | undefined) {
  return useQuery({
    queryKey: settlementKeys.batchDetail(batchRef ?? ''),
    queryFn: ({ signal }) => fetchBatch(batchRef!, signal),
    enabled: Boolean(batchRef),
  });
}

export function useSettlementWindows() {
  return useQuery({
    queryKey: settlementKeys.windows(),
    queryFn: ({ signal }) => fetchSettlementWindows(signal),
  });
}

export function useReconciliationSummary() {
  return useQuery({
    queryKey: settlementKeys.reconciliationSummary(),
    queryFn: ({ signal }) => fetchReconciliationSummary(signal),
  });
}

export function useLedgerEntries(params: LedgerListParams, enabled = true) {
  return useQuery({
    queryKey: settlementKeys.ledger(params),
    queryFn: ({ signal }) => fetchLedgerEntries(params, signal),
    enabled,
  });
}

export function useReconcileBatch(batchRef: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reconcileBatch(batchRef),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: settlementKeys.batchDetail(batchRef) });
      void queryClient.invalidateQueries({ queryKey: settlementKeys.batches() });
      void queryClient.invalidateQueries({ queryKey: settlementKeys.reconciliationSummary() });
      void queryClient.invalidateQueries({ queryKey: ['payments'] });
      void queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });
}
