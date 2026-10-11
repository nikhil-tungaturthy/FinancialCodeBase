import { MousePointerClick, Search, X } from 'lucide-react';
import type { FormEvent } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { CountdownChip } from '@/components/ui/CountdownChip';
import { DataTable, type DataTableColumn, type SortState } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Input } from '@/components/ui/Input';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { Pagination } from '@/components/ui/Pagination';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton, SkeletonLines } from '@/components/ui/Skeleton';
import { SplitPane } from '@/components/ui/SplitPane';
import { StatusPill } from '@/components/ui/StatusPill';
import { ExceptionDetailPanel } from '@/features/exceptions/components/ExceptionDetailPanel';
import { useException, useExceptions, useExceptionSummary } from '@/features/exceptions/hooks';
import { ApiError } from '@/lib/api-client';
import { formatInteger } from '@/lib/format';
import { patchParams, readEnum, readInt, readString } from '@/lib/url-state';
import type { ExceptionListParams, ExceptionQueueItem } from '@/types/api';
import {
  EXCEPTION_STATUS_LABELS,
  EXCEPTION_STATUSES,
  SEVERITIES,
  SEVERITY_LABELS,
  type ExceptionStatus,
} from '@/types/domain';

const OPEN_STATUSES: readonly ExceptionStatus[] = [
  'OPEN',
  'IN_REVIEW',
  'PENDING_APPROVAL',
  'ESCALATED',
];
const VIEW_OPEN = 'open';
const VIEW_ALL = 'all';
const ALL = '__all__';
const SORT_FIELDS = ['due_by', 'opened_at', 'severity', 'amount', 'exception_ref'] as const;

const COLUMNS: DataTableColumn<ExceptionQueueItem>[] = [
  {
    id: 'exception_ref',
    header: 'Exception',
    sortable: true,
    width: '140px',
    cell: (e) => (
      <span className="font-mono text-xs font-medium text-navy-900">
        {e.exception_ref}
        <span className="block text-[11px] font-normal text-slate-500">{e.payment_ref}</span>
      </span>
    ),
  },
  {
    id: 'severity',
    header: 'Severity',
    sortable: true,
    cell: (e) => <SeverityBadge severity={e.severity} />,
  },
  {
    id: 'reason',
    header: 'Reason',
    cell: (e) => (
      <span className="block max-w-[260px]">
        <span className="block truncate font-medium text-navy-900">{e.reason_title}</span>
        <span className="block truncate text-[11px] text-slate-500">{e.customer_name}</span>
      </span>
    ),
  },
  {
    id: 'amount',
    header: 'Amount',
    sortable: true,
    align: 'right',
    cell: (e) => <Money amount={e.amount} currency={e.currency} muteCode className="font-medium" />,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (e) => <StatusPill kind="exception" status={e.status} size="sm" />,
  },
  {
    id: 'due_by',
    header: 'Due',
    sortable: true,
    cell: (e) => <CountdownChip dueBy={e.due_by} size="sm" />,
  },
  {
    id: 'assignee',
    header: 'Assignee',
    hideBelow: 'xl',
    cell: (e) =>
      e.assigned_to ? (
        <span className="text-slate-700">{e.assigned_to.display_name}</span>
      ) : (
        <span className="text-slate-400">Unassigned</span>
      ),
  },
];

function QueueSummary() {
  const summary = useExceptionSummary();
  if (summary.isPending) return <Skeleton className="h-6 w-64" />;
  if (summary.isError || !summary.data) return null;
  const byStatus = summary.data.by_status;
  return (
    <>
      {OPEN_STATUSES.map((status) => (
        <Badge key={status} tone="neutral" size="sm" title={EXCEPTION_STATUS_LABELS[status]}>
          <span className="tnum font-semibold text-navy-900">
            {formatInteger(byStatus[status] ?? 0)}
          </span>
          &nbsp;
          {EXCEPTION_STATUS_LABELS[status].toLowerCase()}
        </Badge>
      ))}
    </>
  );
}

function DetailPane({ exceptionRef }: { exceptionRef: string | undefined }) {
  const query = useException(exceptionRef);

  if (!exceptionRef) {
    return (
      <Card
        className="flex min-h-[420px] flex-1 items-center justify-center"
        data-testid="exception-detail"
      >
        <EmptyState
          icon={MousePointerClick}
          title="Select an exception to review"
          description="Choose a row from the queue to see the held payment, validation evidence and activity."
        />
      </Card>
    );
  }

  if (query.isPending) {
    return (
      <Card className="flex-1 p-5" data-testid="exception-detail" aria-busy="true">
        <Skeleton className="mb-4 h-6 w-48" />
        <SkeletonLines lines={8} />
      </Card>
    );
  }

  if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.isNotFound;
    return (
      <Card className="flex-1" data-testid="exception-detail">
        {notFound ? (
          <EmptyState
            title="Exception not found"
            description={
              <>
                No exception with reference{' '}
                <code className="rounded bg-slate-100 px-1">{exceptionRef}</code> exists.
              </>
            }
          />
        ) : (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
            retrying={query.isRefetching}
          />
        )}
      </Card>
    );
  }

  return <ExceptionDetailPanel detail={query.data} />;
}

export default function ExceptionsPage() {
  const navigate = useNavigate();
  const { exceptionRef } = useParams<{ exceptionRef: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = readInt(searchParams, 'page', 1);
  const pageSize = readInt(searchParams, 'page_size', 25);
  const search = readString(searchParams, 'search');
  const view = readString(searchParams, 'view') ?? VIEW_OPEN;
  const status = readEnum(searchParams, 'status', EXCEPTION_STATUSES);
  const severity = readEnum(searchParams, 'severity', SEVERITIES);
  const sort = readEnum(searchParams, 'sort', SORT_FIELDS) ?? 'due_by';
  const order = readEnum(searchParams, 'order', ['asc', 'desc'] as const) ?? 'asc';

  const statusFilter = status ? [status] : view === VIEW_ALL ? undefined : [...OPEN_STATUSES];
  const params: ExceptionListParams = {
    page,
    page_size: pageSize,
    search,
    status: statusFilter,
    severity: severity ? [severity] : undefined,
    sort,
    order,
  };

  const query = useExceptions(params);
  const update = (patch: Parameters<typeof patchParams>[1]) =>
    setSearchParams(patchParams(searchParams, patch));
  const onSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get('search');
    update({ search: typeof value === 'string' ? value.trim() : '' });
  };
  const sortState: SortState = { column: sort, direction: order };
  const hasFilters = Boolean(search || status || severity || view === VIEW_ALL);
  const queryString = searchParams.toString();
  const openException = (ref: string) =>
    navigate(`/exceptions/${ref}${queryString ? `?${queryString}` : ''}`);

  return (
    <div className="flex h-[calc(100dvh-var(--spacing-topbar)-3rem)] min-h-[560px] flex-col">
      <PageHeader
        title="Exception workbench"
        description="Held payments awaiting review, ordered by time to SLA."
        meta={<QueueSummary />}
      />

      <SplitPane
        className="min-h-0 flex-1"
        leftLabel="Exception queue"
        rightLabel="Exception detail"
        left={
          <Card className="flex min-h-0 flex-1 flex-col">
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-3 py-2.5">
              <form
                onSubmit={onSearchSubmit}
                className="flex min-w-48 flex-1 items-center gap-2"
                role="search"
              >
                <Input
                  key={search ?? ''}
                  name="search"
                  defaultValue={search ?? ''}
                  placeholder="Search ref, payment, customer…"
                  aria-label="Search exceptions"
                  leadingIcon={<Search />}
                  inputSize="sm"
                />
              </form>
              <Select
                value={status ?? view}
                onValueChange={(value) =>
                  value === VIEW_OPEN || value === VIEW_ALL
                    ? update({ view: value, status: null })
                    : update({ status: value, view: null })
                }
              >
                <SelectTrigger size="sm" className="w-40" aria-label="Queue view">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={VIEW_OPEN}>Open work</SelectItem>
                  <SelectItem value={VIEW_ALL}>All exceptions</SelectItem>
                  {EXCEPTION_STATUSES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {EXCEPTION_STATUS_LABELS[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={severity ?? ALL}
                onValueChange={(value) => update({ severity: value === ALL ? null : value })}
              >
                <SelectTrigger size="sm" className="w-32" aria-label="Filter by severity">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Any severity</SelectItem>
                  {SEVERITIES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {SEVERITY_LABELS[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {hasFilters && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Clear filters"
                  onClick={() => update({ search: null, status: null, severity: null, view: null })}
                >
                  <X aria-hidden="true" />
                </Button>
              )}
            </div>

            {query.isError ? (
              <ErrorState
                error={query.error}
                onRetry={() => void query.refetch()}
                retrying={query.isRefetching}
                size="sm"
              />
            ) : (
              <>
                <DataTable
                  aria-label="Exception queue"
                  testId="exception-queue"
                  className="min-h-0 flex-1"
                  columns={COLUMNS}
                  rows={query.data?.items ?? []}
                  rowKey={(e) => e.exception_ref}
                  isLoading={query.isPending}
                  sort={sortState}
                  onSortChange={(next) => update({ sort: next.column, order: next.direction })}
                  onRowClick={(e) => openException(e.exception_ref)}
                  selectedRowKey={exceptionRef ?? null}
                  skeletonRows={8}
                  emptyState={
                    <EmptyState
                      title={hasFilters ? 'No exceptions match' : 'Queue is clear'}
                      description={
                        hasFilters
                          ? 'Adjust the search or filters to see more.'
                          : 'There are no open exceptions awaiting review.'
                      }
                      size="sm"
                    />
                  }
                />
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={query.data?.total ?? 0}
                  itemLabel="exceptions"
                  onPageChange={(next) => update({ page: next })}
                />
              </>
            )}
          </Card>
        }
        right={<DetailPane exceptionRef={exceptionRef} />}
      />
    </div>
  );
}
