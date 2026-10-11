import { apiGet, apiPost } from '@/lib/api-client';
import type {
  ApprovalDecisionRequest,
  ApprovalDetail,
  ApprovalListParams,
  ApprovalSummary,
  Page,
} from '@/types/api';

export function fetchApprovals(
  params: ApprovalListParams = {},
  signal?: AbortSignal,
): Promise<Page<ApprovalSummary>> {
  return apiGet<Page<ApprovalSummary>>('/approvals', {
    query: { status: params.status, page: params.page, page_size: params.page_size },
    signal,
  });
}

export function fetchApproval(approvalRef: string, signal?: AbortSignal): Promise<ApprovalDetail> {
  return apiGet<ApprovalDetail>(`/approvals/${encodeURIComponent(approvalRef)}`, { signal });
}

/** Records an APPROVED / REJECTED decision; the API enforces role and segregation of duties. */
export function decideApproval(
  approvalRef: string,
  body: ApprovalDecisionRequest,
): Promise<ApprovalDetail> {
  return apiPost<ApprovalDetail>(`/approvals/${encodeURIComponent(approvalRef)}/decision`, body);
}
