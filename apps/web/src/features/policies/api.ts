import { apiGet } from '@/lib/api-client';
import type {
  BusinessRule,
  ExceptionReasonPolicyResponse,
  FeeSchedule,
  SettlementCutoffPolicy,
} from '@/types/api';

/**
 * Policy endpoints return small reference collections. Until the generated
 * OpenAPI types pin the exact envelope, accept either a bare array, the
 * standard `{items}` page envelope, or a named collection key.
 */
function unwrapCollection<T>(payload: unknown, namedKeys: readonly string[]): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    for (const key of ['items', ...namedKeys]) {
      const value = record[key];
      if (Array.isArray(value)) return value as T[];
    }
  }
  return [];
}

export function fetchExceptionReasonPolicies(
  signal?: AbortSignal,
): Promise<ExceptionReasonPolicyResponse> {
  return apiGet<ExceptionReasonPolicyResponse>('/policies/exception-reasons', { signal });
}

export function fetchSettlementCutoffPolicies(
  signal?: AbortSignal,
): Promise<SettlementCutoffPolicy[]> {
  return apiGet<unknown>('/policies/settlement-cutoffs', { signal }).then((payload) =>
    unwrapCollection<SettlementCutoffPolicy>(payload, ['rails', 'cutoffs']),
  );
}

export function fetchBusinessRules(signal?: AbortSignal): Promise<BusinessRule[]> {
  return apiGet<unknown>('/policies/business-rules', { signal }).then((payload) =>
    unwrapCollection<BusinessRule>(payload, ['rules']),
  );
}

export function fetchFeeSchedules(signal?: AbortSignal): Promise<FeeSchedule[]> {
  return apiGet<unknown>('/policies/fee-schedules', { signal }).then((payload) =>
    unwrapCollection<FeeSchedule>(payload, ['schedules', 'fee_schedules']),
  );
}
