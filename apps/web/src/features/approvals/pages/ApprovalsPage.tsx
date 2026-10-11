import { X } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { CountdownChip } from '@/components/ui/CountdownChip';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { KeyValueList } from '@/components/ui/KeyValueList';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { Pagination } from '@/components/ui/Pagination';
import { RefLink } from '@/components/ui/RefLink';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton, SkeletonLines } from '@/components/ui/Skeleton';
import { StatusPill } from '@/components/ui/StatusPill';
import { useApproval, useApprovals } from '@/features/approvals/hooks';
import { displayNameFromUsername } from '@/lib/format';
import { patchParams, readEnum, readInt } from '@/lib/url-state';
import type { ApprovalListParams, ApprovalSummary } from '@/types/api';
import {
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUSES,
  APPROVAL_SUBJECT_LABELS,
  ROLE_LABELS,
  humanize,
} from '@/types/domain';

const ALL = '__all__';

function effectiveStatus(a: ApprovalSummary): string {
  return a.status === 'PENDING' && a.is_expired ? 'EXPIRED' : a.status;
}

const COLUMNS: DataTableColumn<ApprovalSummary>[] = [
  {
    id: 'approval_ref',
    header: 'Approval',
    width: '130px',
    cell: (a) => (
      <span className="font-mono text-xs font-medium text-navy-900">{a.approval_ref}</span>
    ),
  },
  {
    id: 'subject',
    header: 'Subject',
    cell: (a) => (
      <span className="block max-w-[320px]">
        <span className="block truncate font-medium text-navy-900">{a.summary}</span>
        <span className="block truncate text-[11px] text-slate-500">
          {APPROVAL_SUBJECT_LABELS[a.subject_type] ?? humanize(a.subject_type)} · {a.subject_ref}
        </span>
      </span>
    ),
  },
  {
    id: 'payment',
    header: 'Payment',
    hideBelow: 'lg',
    cell: (a) =>
      a.payment_ref ? (
        <RefLink to={`/payments/${a.payment_ref}`}>{a.payment_ref}</RefLink>
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
  {
    id: 'action',
    header: 'Requested action',
    hideBelow: 'xl',
    cell: (a) => <span className="text-slate-700">{humanize(a.requested_action)}</span>,
  },
  {
    id: 'amount',
    header: 'Amount',
    align: 'right',
    cell: (a) =>
      a.amount && a.currency ? (
        <Money amount={a.amount} currency={a.currency} muteCode className="font-medium" />
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
  { id: 'risk', header: 'Risk', cell: (a) => <SeverityBadge severity={a.risk_level} /> },
  {
    id: 'role',
    header: 'Requires',
    hideBelow: 'lg',
    cell: (a) => (
      <Badge tone="navy" size="sm">
        {ROLE_LABELS[a.required_role] ?? humanize(a.required_role)}
      </Badge>
    ),
  },
  {
    id: 'requested_by',
    header: 'Requested by',
    hideBelow: 'xl',
    cell: (a) => <span className="text-slate-700">{a.requested_by.display_name}</span>,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (a) => <StatusPill kind="approval" status={effectiveStatus(a)} size="sm" />,
  },
  {
    id: 'expires',
    header: 'Expires',
    cell: (a) =>
      a.status === 'PENDING' ? (
        <CountdownChip dueBy={a.expires_at} size="sm" prefix="Expires in" />
      ) : (
        <DateTime value={a.decided_at ?? a.expires_at} className="text-slate-500" />
      ),
  },
];

function ApprovalDrawer({ approvalRef, onClose }: { approvalRef: string; onClose: () => void }) {
  const query = useApproval(approvalRef);
  const detail = query.data;
  return (
    <Drawer open onOpenChange={(open) => !open && onClose()}>
      <DrawerContent aria-describedby={undefined} data-testid="approval-detail">
        <DrawerHeader>
          <DrawerTitle className="font-mono">{approvalRef}</DrawerTitle>
          <DrawerDescription>
            {detail
              ? `${APPROVAL_SUBJECT_LABELS[detail.subject_type] ?? humanize(detail.subject_type)} · ${detail.subject_ref}`
              : 'Approval request'}
          </DrawerDescription>
          {detail && (
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <StatusPill kind="approval" status={effectiveStatus(detail)} size="sm" />
              <SeverityBadge severity={detail.risk_level} />
              {detail.status === 'PENDING' && (
                <CountdownChip dueBy={detail.expires_at} size="sm" prefix="Expires in" />
              )}
            </div>
          )}
        </DrawerHeader>
        <DrawerBody>
          {query.isPending && (
            <div aria-busy="true">
              <Skeleton className="mb-4 h-5 w-40" />
              <SkeletonLines lines={8} />
            </div>
          )}
          {query.isError && (
            <ErrorState
              error={query.error}
              onRetry={() => void query.refetch()}
              retrying={query.isRefetching}
              size="sm"
            />
          )}
          {detail && (
            <div className="space-y-6">
              <section>
                <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  Request
                </h3>
                <p className="text-13 text-slate-800">{detail.summary}</p>
                {detail.justification && (
                  <p className="mt-2 rounded-md bg-slate-50 p-3 text-13 leading-relaxed text-slate-700">
                    {detail.justification}
                  </p>
                )}
              </section>
              <KeyValueList
                columns={2}
                items={[
                  { label: 'Requested action', value: humanize(detail.requested_action) },
                  {
                    label: 'Amount',
                    value:
                      detail.amount && detail.currency ? (
                        <Money amount={detail.amount} currency={detail.currency} />
                      ) : null,
                  },
                  {
                    label: 'Payment',
                    value: detail.payment_ref ? (
                      <RefLink to={`/payments/${detail.payment_ref}`}>{detail.payment_ref}</RefLink>
                    ) : null,
                  },
                  {
                    label: 'Required role',
                    value: ROLE_LABELS[detail.required_role] ?? humanize(detail.required_role),
                  },
                  {
                    label: 'Requested by',
                    value: detail.requested_by.display_name,
                    hint: `@${detail.requested_by.username}`,
                  },
                  { label: 'Created', value: <DateTime value={detail.created_at} /> },
                  { label: 'Expires', value: <DateTime value={detail.expires_at} /> },
                  { label: 'Decided', value: <DateTime value={detail.decided_at} /> },
                ]}
              />
              <section>
                <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  Your eligibility
                </h3>
                <p className="text-13 text-slate-700">
                  {detail.can_decide.allowed ? (
                    <Badge tone="success" size="sm">
                      Can decide
                    </Badge>
                  ) : (
                    <>
                      <Badge tone="neutral" size="sm">
                        Cannot decide
                      </Badge>
                      {detail.can_decide.reason && (
                        <span className="ml-2 text-slate-500">{detail.can_decide.reason}</span>
                      )}
                    </>
                  )}
                </p>
              </section>
              <section>
                <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  Decisions
                </h3>
                {detail.decisions.length === 0 ? (
                  <p className="text-13 text-slate-500">No decision has been recorded.</p>
                ) : (
                  <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
                    {detail.decisions.map((decision, index) => (
                      <li key={index} className="px-3 py-2.5 text-13">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-navy-900">
                            <StatusPill kind="approval" status={decision.decision} size="sm" />
                          </span>
                          <span className="text-xs text-slate-500">
                            {displayNameFromUsername(decision.decided_by)}
                            {decision.decided_at && (
                              <>
                                {' · '}
                                <DateTime value={decision.decided_at} />
                              </>
                            )}
                          </span>
                        </div>
                        <p className="mt-1 text-slate-700">{decision.rationale}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          )}
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}

export default function ApprovalsPage() {
  const navigate = useNavigate();
  const { approvalRef } = useParams<{ approvalRef: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readInt(searchParams, 'page', 1);
  const pageSize = readInt(searchParams, 'page_size', 25);
  const status = readEnum(searchParams, 'status', APPROVAL_STATUSES);

  const params: ApprovalListParams = {
    page,
    page_size: pageSize,
    status: status ? [status] : undefined,
  };
  const query = useApprovals(params);
  const update = (patch: Parameters<typeof patchParams>[1]) =>
    setSearchParams(patchParams(searchParams, patch));
  const queryString = searchParams.toString();
  const suffix = queryString ? `?${queryString}` : '';

  return (
    <div className="space-y-4">
      <PageHeader
        title="Approvals"
        description="Four-eyes decisions for releases, cancellations and fee adjustments. Deciders must hold the required role and may not approve their own requests."
      />
      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
          <Select
            value={status ?? ALL}
            onValueChange={(value) => update({ status: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-44" aria-label="Filter by approval status">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {APPROVAL_STATUSES.map((value) => (
                <SelectItem key={value} value={value}>
                  {APPROVAL_STATUS_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {status && (
            <Button variant="ghost" size="sm" onClick={() => update({ status: null })}>
              <X aria-hidden="true" />
              Clear
            </Button>
          )}
        </div>
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
            retrying={query.isRefetching}
          />
        ) : (
          <>
            <DataTable
              aria-label="Approval requests"
              testId="approvals-table"
              columns={COLUMNS}
              rows={query.data?.items ?? []}
              rowKey={(a) => a.approval_ref}
              isLoading={query.isPending}
              selectedRowKey={approvalRef ?? null}
              onRowClick={(a) => navigate(`/approvals/${a.approval_ref}${suffix}`)}
              emptyState={
                <EmptyState
                  title={
                    status
                      ? `No ${APPROVAL_STATUS_LABELS[status].toLowerCase()} approvals`
                      : 'No approval requests'
                  }
                  size="sm"
                />
              }
            />
            <Pagination
              page={page}
              pageSize={pageSize}
              total={query.data?.total ?? 0}
              itemLabel="approvals"
              onPageChange={(next) => update({ page: next })}
            />
          </>
        )}
      </Card>
      {approvalRef && (
        <ApprovalDrawer approvalRef={approvalRef} onClose={() => navigate(`/approvals${suffix}`)} />
      )}
    </div>
  );
}
