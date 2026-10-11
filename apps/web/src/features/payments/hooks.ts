import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  cancelPayment,
  fetchPayment,
  fetchPayments,
  revalidatePayment,
} from '@/features/payments/api';
import type { PaymentListParams } from '@/types/api';

export const paymentKeys = {
  all: ['payments'] as const,
  lists: () => [...paymentKeys.all, 'list'] as const,
  list: (params: PaymentListParams) => [...paymentKeys.lists(), params] as const,
  details: () => [...paymentKeys.all, 'detail'] as const,
  detail: (paymentRef: string) => [...paymentKeys.details(), paymentRef] as const,
};

export function usePayments(params: PaymentListParams) {
  return useQuery({
    queryKey: paymentKeys.list(params),
    queryFn: ({ signal }) => fetchPayments(params, signal),
    placeholderData: keepPreviousData,
  });
}

export function usePayment(paymentRef: string | undefined) {
  return useQuery({
    queryKey: paymentKeys.detail(paymentRef ?? ''),
    queryFn: ({ signal }) => fetchPayment(paymentRef!, signal),
    enabled: Boolean(paymentRef),
  });
}

export function useRevalidatePayment(paymentRef: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => revalidatePayment(paymentRef),
    onSuccess: (detail) => {
      queryClient.setQueryData(paymentKeys.detail(paymentRef), detail);
      void queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
    },
  });
}

export function useCancelPayment(paymentRef: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body?: { reason?: string }) => cancelPayment(paymentRef, body),
    onSuccess: (detail) => {
      queryClient.setQueryData(paymentKeys.detail(paymentRef), detail);
      void queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
    },
  });
}
