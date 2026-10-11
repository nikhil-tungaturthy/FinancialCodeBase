import { useQuery } from '@tanstack/react-query';

import {
  fetchBusinessRules,
  fetchExceptionReasonPolicies,
  fetchFeeSchedules,
  fetchSettlementCutoffPolicies,
} from '@/features/policies/api';

export const policyKeys = {
  all: ['policies'] as const,
  exceptionReasons: () => [...policyKeys.all, 'exception-reasons'] as const,
  settlementCutoffs: () => [...policyKeys.all, 'settlement-cutoffs'] as const,
  businessRules: () => [...policyKeys.all, 'business-rules'] as const,
  feeSchedules: () => [...policyKeys.all, 'fee-schedules'] as const,
};

const POLICY_STALE_TIME = 5 * 60_000;

export function useExceptionReasonPolicies() {
  return useQuery({
    queryKey: policyKeys.exceptionReasons(),
    queryFn: ({ signal }) => fetchExceptionReasonPolicies(signal),
    staleTime: POLICY_STALE_TIME,
  });
}

export function useSettlementCutoffPolicies() {
  return useQuery({
    queryKey: policyKeys.settlementCutoffs(),
    queryFn: ({ signal }) => fetchSettlementCutoffPolicies(signal),
    staleTime: POLICY_STALE_TIME,
  });
}

export function useBusinessRules() {
  return useQuery({
    queryKey: policyKeys.businessRules(),
    queryFn: ({ signal }) => fetchBusinessRules(signal),
    staleTime: POLICY_STALE_TIME,
  });
}

export function useFeeSchedules() {
  return useQuery({
    queryKey: policyKeys.feeSchedules(),
    queryFn: ({ signal }) => fetchFeeSchedules(signal),
    staleTime: POLICY_STALE_TIME,
  });
}
