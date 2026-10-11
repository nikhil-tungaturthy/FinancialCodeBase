import { Layers, Scale, TriangleAlert, X } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { KpiTile } from '@/components/ui/KpiTile';
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
import { useBatches, useReconciliationSummary } from '@/features/settlement/hooks';
import { formatInteger, pluralize } from '@/lib/format';
import { formatMoney } from '@/lib/money';
import { patchParams, readEnum, readInt } from '@/lib/url-state';
import type { BatchListParams, BatchSummary } from '@/types/api';
import { BATCH_STATUS_LABELS, BATCH_STATUSES, RAIL_LABELS, RAILS } from '@/types/domain';

const ALL = '__all__';

const COLUMNS: DataTableColumn<BatchSummary>[] = [
  {
    id: 'batch_ref',
    header: 'Batch',
    width: '200px',
    cell: (b) => <RefLink to={`/settlement/batches/${b.batch_ref}`}>{b.batch_ref}</RefLink>,
  },
  {
    id: 'rail',
    header: 'Rail',
    cell: (b) => (
      <span className="font-medium text-navy-900">
        {RAIL_LABELS[b.rail] ?? b.rail} <span className="text-slate-400">· {b.currency}</span>
      </span>
    ),
  },
  {
    id: 'value_date',
    header: 'Value date',
    cell: (b) => <DateTime value={b.value_date} mode="date" />,
  },
  {
    id: 'cutoff',
    header: 'Cutoff',
    hideBelow: 'xl',
    cell: (b) => <DateTime value={b.cutoff_at} className="text-slate-600" />,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (b) => <StatusPill kind="batch" status={b.status} size="sm" />,
  },
  {
    id: 'entries',
    header: 'Entries',
    align: 'right',
    cell: (b) => <span className="tnum">{formatInteger(b.entry_count)}</span>,
  },
  {
    id: 'expected',
    header: 'Expected',
    align: 'right',
    cell: (b) => <Money amount={b.expected_total} currency={b.currency} muteCode />,
  },
  {
    id: 'recorded',
    header: 'Recorded',
    align: 'right',
    hideBelow: 'lg',
    cell: (b) => (
      <Money amount={b.recorded_total} currency={b.currency} muteCode className="text-slate-600" />
    ),
  },
  {
    id: 'variance',
    header: 'Variance',
    align: 'right',
    cell: (b) =>
      b.variance === null || b.variance === undefined ? (
        <span className="text-slate-300">—</span>
      ) : (
        <Money
          amount={b.variance}
          currency={b.currency}
          withCode={false}
          signed
          colorBySign
          className="font-medium"
        />
      ),
  },
  {
    id: 'recon',
    header: 'Reconciliation',
    cell: (b) => <StatusPill kind="reconciliation" status={b.reconciliation_status} size="sm" />,
  },
];

function SummaryTiles() {
  const summary = useReconciliationSummary();
  const data = summary.data;
  const discrepancies = data?.by_status.DISCREPANCY ?? data?.open_discrepancies.length ?? 0;
  const variance = data?.total_variance_by_currency.filter((v) => Number(v.variance) !== 0) ?? [];
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" data-testid="settlement-summary">
      <KpiTile
        label="Settlement batches"
        value={formatInteger(data?.batches_total)}
        subtext={
          data
            ? `${formatInteger(data.by_status.RECONCILED ?? 0)} reconciled · ${formatInteger(data.by_status.OPEN ?? 0)} open`
            : undefined
        }
        icon={Layers}
        isLoading={summary.isPending}
      />
      <KpiTile
        label="Open discrepancies"
        value={formatInteger(discrepancies)}
        subtext={
          discrepancies > 0
            ? pluralize(discrepancies, 'batch', 'batches') + ' with unmatched entries'
            : 'All reconciled batches matched'
        }
        subtextTone={discrepancies > 0 ? 'danger' : 'success'}
        icon={TriangleAlert}
        iconTone={discrepancies > 0 ? 'danger' : 'success'}
        isLoading={summary.isPending}
      />
      <KpiTile
        label="Net variance"
        value={
          variance.length === 0
            ? '0'
            : variance.map((v) => formatMoney(v.variance, v.currency, { signed: true })).join(' · ')
        }
        subtext="Recorded ledger credits minus expected settlement"
        icon={Scale}
        iconTone="navy"
        isLoading={summary.isPending}
      />
    </div>
  );
}

export default function SettlementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readInt(searchParams, 'page', 1);
  const pageSize = readInt(searchParams, 'page_size', 25);
  const status = readEnum(searchParams, 'status', BATCH_STATUSES);
  const rail = readEnum(searchParams, 'rail', RAILS);

  const params: BatchListParams = {
    page,
    page_size: pageSize,
    status: status ? [status] : undefined,
    rail: rail ? [rail] : undefined,
  };
  const query = useBatches(params);
  const update = (patch: Parameters<typeof patchParams>[1]) =>
    setSearchParams(patchParams(searchParams, patch));
  const hasFilters = Boolean(status || rail);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Settlement & reconciliation"
        description="Settlement batches per rail and value date, with ledger reconciliation outcome."
      />
      <SummaryTiles />
      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
          <Select
            value={status ?? ALL}
            onValueChange={(value) => update({ status: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-44" aria-label="Filter by batch status">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {BATCH_STATUSES.map((value) => (
                <SelectItem key={value} value={value}>
                  {BATCH_STATUS_LABELS[value]}
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
              {RAILS.map((value) => (
                <SelectItem key={value} value={value}>
                  {RAIL_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={() => update({ status: null, rail: null })}>
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
              aria-label="Settlement batches"
              testId="batch-table"
              columns={COLUMNS}
              rows={query.data?.items ?? []}
              rowKey={(b) => b.batch_ref}
              isLoading={query.isPending}
              onRowClick={(b) => navigate(`/settlement/batches/${b.batch_ref}`)}
              defaultSort={{ column: 'value_date', direction: 'desc' }}
              emptyState={
                <EmptyState
                  title={hasFilters ? 'No batches match these filters' : 'No settlement batches'}
                  size="sm"
                />
              }
            />
            <Pagination
              page={page}
              pageSize={pageSize}
              total={query.data?.total ?? 0}
              itemLabel="batches"
              onPageChange={(next) => update({ page: next })}
              onPageSizeChange={(next) => update({ page_size: next })}
            />
          </>
        )}
      </Card>
    </div>
  );
}
