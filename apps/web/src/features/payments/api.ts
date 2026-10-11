import { apiGet, apiPost } from '@/lib/api-client';
import type { Page, PaymentDetail, PaymentListParams, PaymentSummary } from '@/types/api';

export function fetchPayments(
  params: PaymentListParams = {},
  signal?: AbortSignal,
): Promise<Page<PaymentSummary>> {
  return apiGet<Page<PaymentSummary>>('/payments', {
    query: {
      search: params.search,
      status: params.status,
      rail: params.rail,
      currency: params.currency,
      priority: params.priority,
      risk_tier: params.risk_tier,
      date_from: params.date_from,
      date_to: params.date_to,
      sort: params.sort,
      order: params.order,
      page: params.page,
      page_size: params.page_size,
    },
    signal,
  });
}

export function fetchPayment(paymentRef: string, signal?: AbortSignal): Promise<PaymentDetail> {
  return apiGet<PaymentDetail>(`/payments/${encodeURIComponent(paymentRef)}`, { signal });
}

/** Re-runs validation for CREATED/HELD payments (ANALYST+). */
export function revalidatePayment(paymentRef: string): Promise<PaymentDetail> {
  return apiPost<PaymentDetail>(`/payments/${encodeURIComponent(paymentRef)}/revalidate`);
}

/** Cancels a payment (SUPERVISOR+). */
export function cancelPayment(
  paymentRef: string,
  body?: { reason?: string },
): Promise<PaymentDetail> {
  return apiPost<PaymentDetail>(`/payments/${encodeURIComponent(paymentRef)}/cancel`, body);
}
