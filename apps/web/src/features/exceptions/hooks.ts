import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addExceptionNote,
  assignException,
  fetchException,
  fetchExceptions,
  fetchExceptionSummary,
  performExceptionAction,
} from '@/features/exceptions/api';
import { paymentKeys } from '@/features/payments/hooks';
import type {
  AddExceptionNoteRequest,
  AssignExceptionRequest,
  ExceptionActionRequest,
  ExceptionDetail,
  ExceptionListParams,
} from '@/types/api';

export const exceptionKeys = {
  all: ['exceptions'] as const,
  lists: () => [...exceptionKeys.all, 'list'] as const,
  list: (params: ExceptionListParams) => [...exceptionKeys.lists(), params] as const,
  summary: () => [...exceptionKeys.all, 'summary'] as const,
  details: () => [...exceptionKeys.all, 'detail'] as const,
  detail: (exceptionRef: string) => [...exceptionKeys.details(), exceptionRef] as const,
};

export function useExceptions(params: ExceptionListParams) {
  return useQuery({
    queryKey: exceptionKeys.list(params),
    queryFn: ({ signal }) => fetchExceptions(params, signal),
    placeholderData: keepPreviousData,
  });
}

export function useExceptionSummary() {
  return useQuery({
    queryKey: exceptionKeys.summary(),
    queryFn: ({ signal }) => fetchExceptionSummary(signal),
  });
}

export function useException(exceptionRef: string | undefined) {
  return useQuery({
    queryKey: exceptionKeys.detail(exceptionRef ?? ''),
    queryFn: ({ signal }) => fetchException(exceptionRef!, signal),
    enabled: Boolean(exceptionRef),
  });
}

/** Shared cache updates after any write against an exception. */
function useExceptionWriteEffects(exceptionRef: string) {
  const queryClient = useQueryClient();
  return (detail: ExceptionDetail) => {
    queryClient.setQueryData(exceptionKeys.detail(exceptionRef), detail);
    void queryClient.invalidateQueries({ queryKey: exceptionKeys.lists() });
    void queryClient.invalidateQueries({ queryKey: exceptionKeys.summary() });
    void queryClient.invalidateQueries({
      queryKey: paymentKeys.detail(detail.payment.payment_ref),
    });
    void queryClient.invalidateQueries({ queryKey: paymentKeys.lists() });
  };
}

export function useAssignException(exceptionRef: string) {
  const onWrite = useExceptionWriteEffects(exceptionRef);
  return useMutation({
    mutationFn: (body: AssignExceptionRequest) => assignException(exceptionRef, body),
    onSuccess: onWrite,
  });
}

export function useAddExceptionNote(exceptionRef: string) {
  const onWrite = useExceptionWriteEffects(exceptionRef);
  return useMutation({
    mutationFn: (body: AddExceptionNoteRequest) => addExceptionNote(exceptionRef, body),
    onSuccess: onWrite,
  });
}

export function usePerformExceptionAction(exceptionRef: string) {
  const onWrite = useExceptionWriteEffects(exceptionRef);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ExceptionActionRequest) => performExceptionAction(exceptionRef, body),
    onSuccess: (response) => {
      onWrite(response);
      void queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
  });
}
