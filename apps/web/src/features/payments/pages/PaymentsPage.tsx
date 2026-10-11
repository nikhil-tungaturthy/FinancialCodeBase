import { Search, X } from 'lucide-react';
import { type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable, type DataTableColumn, type SortState } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Input } from '@/components/ui/Input';
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
import { StatusPill } from '@/components/ui/StatusPill';
import { usePayments } from '@/features/payments/hooks';
import { patchParams, readEnum, readInt, readString } from '@/lib/url-state';
import type { PaymentListParams, PaymentSortField, PaymentSummary } from '@/types/api';
import {
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUSES,
  PRIORITY_LABELS,
  PRIORITY_TONES,
  RAIL_LABELS,
  RAILS,
  RISK_TIER_LABELS,
  RISK_TIER_TONES,
  type PaymentStatus,
  type Rail,
} from '@/types/domain';

const SORT_FIELDS: readonly PaymentSortField[] = [
  'created_at',
  'amount',
  'status',
  'payment_ref',
  'customer',
];
const ALL = '__all__';

const COLUMNS: DataTableColumn<PaymentSummary>[] = [
  {
    id: 'payment_ref',
    header: 'Payment',
    sortable: true,
    width: '150px',
    cell: (p) => <RefLink to={`/payments/${p.payment_ref}`}>{p.payment_ref}</RefLink>,
  },
  {
    id: 'created_at',
    header: 'Created',
    sortable: true,
    cell: (p) => <DateTime value={p.created_at} className="text-slate-600" />,
  },
  {
    id: 'customer',
    header: 'Customer',
    sortable: true,
    cell: (p) => <span className="font-medium text-navy-900">{p.customer_name}</span>,
  },
  {
    id: 'beneficiary',
    header: 'Beneficiary',
    hideBelow: 'xl',
    cell: (p) => <span className="text-slate-700">{p.beneficiary_name}</span>,
  },
  {
    id: 'rail',
    header: 'Rail',
    cell: (p) => <span className="text-slate-700">{RAIL_LABELS[p.rail] ?? p.rail}</span>,
  },
  {
    id: 'amount',
    header: 'Amount',
    sortable: true,
    align: 'right',
    cell: (p) => <Money amount={p.amount} currency={p.currency} muteCode className="font-medium" />,
  },
  {
    id: 'usd',
    header: 'USD eq.',
    align: 'right',
    hideBelow: 'lg',
    cell: (p) => (
      <Money amount={p.usd_equivalent} currency="USD" withCode={false} className="text-slate-500" />
    ),
  },
  {
    id: 'status',
    header: 'Status',
    sortable: true,
    cell: (p) => <StatusPill kind="payment" status={p.status} size="sm" />,
  },
  {
    id: 'priority',
    header: 'Priority',
    hideBelow: 'lg',
    cell: (p) => (
      <div className="flex items-center gap-1">
        <Badge tone={PRIORITY_TONES[p.priority]} size="sm">
          {PRIORITY_LABELS[p.priority] ?? p.priority}
        </Badge>
        <Badge tone={RISK_TIER_TONES[p.risk_tier]} size="sm" title={RISK_TIER_LABELS[p.risk_tier]}>
          {p.risk_tier}
        </Badge>
      </div>
    ),
  },
  {
    id: 'exception',
    header: 'Exception',
    cell: (p) =>
      p.has_open_exception && p.exception_ref ? (
        <RefLink to={`/exceptions/${p.exception_ref}`}>{p.exception_ref}</RefLink>
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
];

export default function PaymentsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = readInt(searchParams, 'page', 1);
  const pageSize = readInt(searchParams, 'page_size', 25);
  const search = readString(searchParams, 'search');
  const status = readEnum(searchParams, 'status', PAYMENT_STATUSES);
  const rail = readEnum(searchParams, 'rail', RAILS);
  const sort = readEnum(searchParams, 'sort', SORT_FIELDS) ?? 'created_at';
  const order = readEnum(searchParams, 'order', ['asc', 'desc'] as const) ?? 'desc';

  const params: PaymentListParams = {
    page,
    page_size: pageSize,
    search,
    status: status ? [status] : undefined,
    rail: rail ? [rail] : undefined,
    sort,
    order,
  };

  const query = usePayments(params);
  const update = (patch: Parameters<typeof patchParams>[1]) =>
    setSearchParams(patchParams(searchParams, patch));

  const onSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get('search');
    update({ search: typeof value === 'string' ? value.trim() : '' });
  };

  const sortState: SortState = { column: sort, direction: order };
  const hasFilters = Boolean(search || status || rail);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Payments"
        description="Every instruction received across portal, API, file and branch channels, with lifecycle status and settlement window."
      />

      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
          <form
            onSubmit={onSearchSubmit}
            className="flex min-w-64 flex-1 items-center gap-2"
            role="search"
          >
            <Input
              key={search ?? ''}
              name="search"
              defaultValue={search ?? ''}
              placeholder="Search reference, customer, beneficiary…"
              aria-label="Search payments"
              leadingIcon={<Search />}
              inputSize="sm"
              className="max-w-md"
            />
            <Button type="submit" variant="outline" size="sm">
              Search
            </Button>
          </form>
          <Select
            value={status ?? ALL}
            onValueChange={(value) => update({ status: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-44" aria-label="Filter by status">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {PAYMENT_STATUSES.map((value: PaymentStatus) => (
                <SelectItem key={value} value={value}>
                  {PAYMENT_STATUS_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={rail ?? ALL}
            onValueChange={(value) => update({ rail: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-40" aria-label="Filter by rail">
              <SelectValue placeholder="All rails" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All rails</SelectItem>
              {RAILS.map((value: Rail) => (
                <SelectItem key={value} value={value}>
                  {RAIL_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => update({ search: null, status: null, rail: null })}
            >
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
              aria-label="Payments"
              testId="payments-table"
              columns={COLUMNS}
              rows={query.data?.items ?? []}
              rowKey={(p) => p.payment_ref}
              isLoading={query.isPending}
              sort={sortState}
              onSortChange={(next) => update({ sort: next.column, order: next.direction })}
              onRowClick={(p) => navigate(`/payments/${p.payment_ref}`)}
              skeletonRows={pageSize > 10 ? 10 : pageSize}
              emptyState={
                <EmptyState
                  title={hasFilters ? 'No payments match these filters' : 'No payments yet'}
                  description={
                    hasFilters
                      ? 'Try widening the search or clearing the status and rail filters.'
                      : 'Seed the database to populate the payment ledger.'
                  }
                  size="sm"
                />
              }
              className={
                query.isFetching && !query.isPending ? 'opacity-70 transition-opacity' : undefined
              }
            />
            <Pagination
              page={page}
              pageSize={pageSize}
              total={query.data?.total ?? 0}
              itemLabel="payments"
              onPageChange={(next) => update({ page: next })}
              onPageSizeChange={(next) => update({ page_size: next })}
            />
          </>
        )}
      </Card>
    </div>
  );
}
