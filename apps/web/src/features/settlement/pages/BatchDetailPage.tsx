import { Check, FileSearch, Minus, X } from 'lucide-react';
import { Link, useParams } from 'react-router';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { KeyValueList } from '@/components/ui/KeyValueList';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { RefLink } from '@/components/ui/RefLink';
import { Skeleton, SkeletonLines } from '@/components/ui/Skeleton';
import { StatusPill } from '@/components/ui/StatusPill';
import { useBatch } from '@/features/settlement/hooks';
import { ApiError } from '@/lib/api-client';
import { formatInteger, orDash } from '@/lib/format';
import type {
  DiscrepancyKind,
  LedgerEntry,
  ReconciliationDiscrepancy,
  SettlementEntry,
} from '@/types/api';
import { RAIL_LABELS } from '@/types/domain';

function MatchedFlag({ matched }: { matched: boolean | null }) {
  if (matched === null) {
    return (
      <span className="inline-flex items-center gap-1 text-slate-400" title="Not reconciled">
        <Minus className="size-3.5" aria-hidden="true" />
        <span className="sr-only">Not reconciled</span>
      </span>
    );
  }
  return matched ? (
    <span className="inline-flex items-center gap-1 text-green-600" title="Matched">
      <Check className="size-3.5" aria-hidden="true" />
      <span className="sr-only">Matched</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 font-medium text-red-600" title="Unmatched">
      <X className="size-3.5" aria-hidden="true" />
      <span className="sr-only">Unmatched</span>
    </span>
  );
}

const DISCREPANCY_KIND_LABELS: Record<DiscrepancyKind, string> = {
  MISSING: 'Missing',
  DUPLICATE: 'Duplicate',
  AMOUNT_MISMATCH: 'Amount mismatch',
};

function InvestigationList({
  items,
  currency,
}: {
  items: ReconciliationDiscrepancy[];
  currency: string;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="mt-4 border-t border-slate-100 pt-3" data-testid="batch-investigation">
      <p className="text-[11px] font-medium tracking-wide text-slate-500 uppercase">
        Investigation
      </p>
      <ul className="mt-1.5 divide-y divide-slate-100">
        {items.map((item) => {
          const key = [
            item.kind,
            item.settlement_entry_ref ?? '',
            item.payment_ref ?? '',
            item.ledger_entry_refs.join(','),
          ].join(':');
          return (
            <li key={key} className="py-2 text-13">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <span className="font-medium text-slate-800">
                  {DISCREPANCY_KIND_LABELS[item.kind]}
                </span>
                <span className="text-xs text-slate-500">
                  Expected{' '}
                  <Money amount={item.expected_amount} currency={currency} muteCode />
                  {' · '}
                  Recorded{' '}
                  <Money amount={item.recorded_amount} currency={currency} muteCode />
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                {item.payment_ref ? (
                  <RefLink to={`/payments/${item.payment_ref}`}>{item.payment_ref}</RefLink>
                ) : null}
                {item.settlement_entry_ref ? (
                  <span className="font-mono text-slate-700">{item.settlement_entry_ref}</span>
                ) : null}
                {item.ledger_entry_refs.map((ref) => (
                  <span key={ref} className="font-mono text-red-700">
                    {ref}
                  </span>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const ENTRY_COLUMNS: DataTableColumn<SettlementEntry>[] = [
  {
    id: 'entry_ref',
    header: 'Entry',
    width: '120px',
    cell: (e) => <span className="font-mono text-xs text-slate-700">{e.entry_ref}</span>,
  },
  {
    id: 'payment_ref',
    header: 'Payment',
    cell: (e) =>
      e.payment_ref ? (
        <RefLink to={`/payments/${e.payment_ref}`}>{e.payment_ref}</RefLink>
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
  {
    id: 'amount',
    header: 'Amount',
    align: 'right',
    sortable: true,
    sortValue: (e) => Number(e.amount),
    cell: (e) => <Money amount={e.amount} currency={e.currency} muteCode className="font-medium" />,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (e) => <StatusPill kind="settlement-entry" status={e.status} size="sm" />,
  },
  {
    id: 'external',
    header: 'Rail reference',
    hideBelow: 'lg',
    cell: (e) => (
      <span className="font-mono text-xs text-slate-600">{orDash(e.external_reference)}</span>
    ),
  },
  {
    id: 'settled_at',
    header: 'Settled',
    hideBelow: 'xl',
    cell: (e) => <DateTime value={e.settled_at} className="text-slate-600" />,
  },
  {
    id: 'matched',
    header: 'Matched',
    align: 'center',
    cell: (e) => <MatchedFlag matched={e.matched} />,
  },
];

const LEDGER_COLUMNS: DataTableColumn<LedgerEntry>[] = [
  {
    id: 'entry_ref',
    header: 'Ledger entry',
    width: '120px',
    cell: (l) => <span className="font-mono text-xs text-slate-700">{l.entry_ref}</span>,
  },
  {
    id: 'journal',
    header: 'Journal',
    cell: (l) => <span className="font-mono text-xs text-slate-600">{l.journal_ref}</span>,
  },
  {
    id: 'payment_ref',
    header: 'Payment',
    cell: (l) =>
      l.payment_ref ? (
        <RefLink to={`/payments/${l.payment_ref}`}>{l.payment_ref}</RefLink>
      ) : (
        <span className="text-slate-300">—</span>
      ),
  },
  {
    id: 'account',
    header: 'Account',
    cell: (l) => <span className="font-mono text-xs">{l.account_code}</span>,
  },
  {
    id: 'leg',
    header: 'Leg',
    hideBelow: 'lg',
    cell: (l) => (
      <span className="text-slate-600">
        {l.leg} · {l.direction}
      </span>
    ),
  },
  {
    id: 'amount',
    header: 'Amount',
    align: 'right',
    cell: (l) => (
      <Money
        amount={l.amount}
        currency={l.currency}
        muteCode
        className={l.direction === 'CREDIT' ? 'font-medium' : 'text-slate-600'}
      />
    ),
  },
  {
    id: 'posted_at',
    header: 'Posted',
    hideBelow: 'xl',
    cell: (l) => <DateTime value={l.posted_at} className="text-slate-600" />,
  },
  {
    id: 'source',
    header: 'Source',
    hideBelow: 'xl',
    cell: (l) => <span className="text-xs text-slate-500">{l.posting_source}</span>,
  },
];

export default function BatchDetailPage() {
  const { batchRef } = useParams<{ batchRef: string }>();
  const query = useBatch(batchRef);

  if (query.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-7 w-72" />
        <Card>
          <CardContent>
            <SkeletonLines lines={6} />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (query.isError) {
    if (query.error instanceof ApiError && query.error.isNotFound) {
      return (
        <Card className="mx-auto max-w-lg">
          <EmptyState
            icon={FileSearch}
            title="Batch not found"
            description={
              <>
                No settlement batch <code className="rounded bg-slate-100 px-1">{batchRef}</code>{' '}
                exists in this environment.
              </>
            }
            action={
              <Button asChild variant="outline">
                <Link to="/settlement">Back to settlement</Link>
              </Button>
            }
          />
        </Card>
      );
    }
    return (
      <Card>
        <ErrorState
          error={query.error}
          onRetry={() => void query.refetch()}
          retrying={query.isRefetching}
        />
      </Card>
    );
  }

  const { batch, entries, ledger_entries: ledgerEntries, reconciliation } = query.data;
  const amountByRef = new Map<string, { amount: string; currency: string }>();
  for (const entry of entries)
    amountByRef.set(entry.entry_ref, { amount: entry.amount, currency: entry.currency });
  for (const ledger of ledgerEntries)
    amountByRef.set(ledger.entry_ref, { amount: ledger.amount, currency: ledger.currency });

  return (
    <div className="space-y-4" data-testid="batch-detail">
      <PageHeader
        eyebrow="Settlement batch"
        breadcrumbs={[{ label: 'Settlement', to: '/settlement' }, { label: batch.batch_ref }]}
        title={<span className="font-mono">{batch.batch_ref}</span>}
        meta={
          <>
            <StatusPill kind="batch" status={batch.status} />
            <StatusPill kind="reconciliation" status={batch.reconciliation_status} />
          </>
        }
        description={`${RAIL_LABELS[batch.rail] ?? batch.rail} · ${batch.currency} · value date ${batch.value_date} · ${formatInteger(batch.entry_count)} entries`}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Batch</CardTitle>
              <CardDescription>Window, cutoff and totals.</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <KeyValueList
              columns={3}
              items={[
                { label: 'Rail', value: RAIL_LABELS[batch.rail] ?? batch.rail },
                { label: 'Currency', value: batch.currency },
                { label: 'Value date', value: <DateTime value={batch.value_date} mode="date" /> },
                { label: 'Window', value: batch.window_key, mono: true },
                {
                  label: 'Cutoff',
                  value: <DateTime value={batch.cutoff_at} />,
                  hint: batch.timezone,
                },
                { label: 'Settled at', value: <DateTime value={batch.settled_at} /> },
                {
                  label: 'Expected total',
                  value: (
                    <Money
                      amount={batch.expected_total}
                      currency={batch.currency}
                      className="font-semibold text-navy-900"
                    />
                  ),
                },
                {
                  label: 'Recorded total',
                  value: <Money amount={batch.recorded_total} currency={batch.currency} />,
                },
                {
                  label: 'Variance',
                  value: (
                    <Money
                      amount={batch.variance}
                      currency={batch.currency}
                      signed
                      colorBySign
                      className="font-semibold"
                    />
                  ),
                },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Latest reconciliation</CardTitle>
              <CardDescription>
                {reconciliation ? (
                  <>
                    Run <span className="font-mono">{reconciliation.run_ref}</span>
                  </>
                ) : (
                  'No reconciliation run recorded.'
                )}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {reconciliation ? (
              <>
                <KeyValueList
                  columns={2}
                  items={[
                    {
                      label: 'Status',
                      value: (
                        <StatusPill
                          kind="reconciliation"
                          status={reconciliation.status}
                          size="sm"
                        />
                      ),
                    },
                    { label: 'Run at', value: <DateTime value={reconciliation.run_at} /> },
                    { label: 'Matched', value: formatInteger(reconciliation.matched_count) },
                    {
                      label: 'Unmatched',
                      value: (
                        <span
                          className={
                            reconciliation.unmatched_count > 0
                              ? 'font-semibold text-red-600'
                              : undefined
                          }
                        >
                          {formatInteger(reconciliation.unmatched_count)}
                        </span>
                      ),
                    },
                    {
                      label: 'Variance',
                      value: (
                        <Money
                          amount={reconciliation.variance}
                          currency={batch.currency}
                          signed
                          colorBySign
                        />
                      ),
                      fullWidth: true,
                    },
                    {
                      label: 'Input hash',
                      value: reconciliation.input_hash,
                      mono: true,
                      fullWidth: true,
                    },
                  ]}
                />
                <InvestigationList
                  items={reconciliation.discrepancies}
                  currency={batch.currency}
                />
                {reconciliation.unmatched_refs.length > 0 && (
                  <div className="mt-4 border-t border-slate-100 pt-3">
                    <p className="text-[11px] font-medium tracking-wide text-slate-500 uppercase">
                      Unmatched entries
                    </p>
                    <ul className="mt-1.5 divide-y divide-slate-100" data-testid="batch-unmatched">
                      {reconciliation.unmatched_refs.map((ref) => {
                        const amount = amountByRef.get(ref);
                        return (
                          <li
                            key={ref}
                            className="flex items-center justify-between py-1.5 text-13"
                          >
                            <span className="font-mono text-xs text-red-700">{ref}</span>
                            {amount ? (
                              <Money amount={amount.amount} currency={amount.currency} muteCode />
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {reconciliation.notes && (
                  <p className="mt-3 text-xs text-slate-600">{reconciliation.notes}</p>
                )}
              </>
            ) : (
              <EmptyState
                title="Not yet reconciled"
                description="Reconciliation runs after the batch settles."
                size="sm"
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Settlement entries</CardTitle>
            <CardDescription>
              {formatInteger(entries.length)} entries · matched flag from the latest reconciliation
              run.
            </CardDescription>
          </div>
        </CardHeader>
        <DataTable
          aria-label="Settlement entries"
          testId="batch-entries"
          columns={ENTRY_COLUMNS}
          rows={entries}
          rowKey={(e) => e.entry_ref}
          maxHeight="520px"
          emptyState={<EmptyState title="No entries in this batch" size="sm" />}
        />
      </Card>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Ledger postings</CardTitle>
            <CardDescription>
              {formatInteger(ledgerEntries.length)} principal and fee legs posted against this
              batch.
            </CardDescription>
          </div>
        </CardHeader>
        <DataTable
          aria-label="Ledger postings"
          testId="batch-ledger"
          columns={LEDGER_COLUMNS}
          rows={ledgerEntries}
          rowKey={(l) => l.entry_ref}
          maxHeight="520px"
          emptyState={<EmptyState title="No ledger postings yet" size="sm" />}
        />
      </Card>
    </div>
  );
}
