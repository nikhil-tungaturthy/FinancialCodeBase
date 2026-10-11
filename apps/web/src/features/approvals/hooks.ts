import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { decideApproval, fetchApproval, fetchApprovals } from '@/features/approvals/api';
import type { ApprovalDecisionRequest, ApprovalListParams } from '@/types/api';

export const approvalKeys = {
  all: ['approvals'] as const,
  lists: () => [...approvalKeys.all, 'list'] as const,
  list: (params: ApprovalListParams) => [...approvalKeys.lists(), params] as const,
  details: () => [...approvalKeys.all, 'detail'] as const,
  detail: (approvalRef: string) => [...approvalKeys.details(), approvalRef] as const,
};

export function useApprovals(params: ApprovalListParams) {
  return useQuery({
    queryKey: approvalKeys.list(params),
    queryFn: ({ signal }) => fetchApprovals(params, signal),
    placeholderData: keepPreviousData,
  });
}

export function useApproval(approvalRef: string | undefined) {
  return useQuery({
    queryKey: approvalKeys.detail(approvalRef ?? ''),
    queryFn: ({ signal }) => fetchApproval(approvalRef!, signal),
    enabled: Boolean(approvalRef),
  });
}

export function useDecideApproval(approvalRef: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ApprovalDecisionRequest) => decideApproval(approvalRef, body),
    onSuccess: (detail) => {
      queryClient.setQueryData(approvalKeys.detail(approvalRef), detail);
      void queryClient.invalidateQueries({ queryKey: approvalKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      void queryClient.invalidateQueries({ queryKey: ['payments'] });
      void queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });
}
