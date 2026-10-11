import { AlertTriangle, ArrowLeftRight, Flame, Hourglass, Wallet } from 'lucide-react';
import { Link } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { CountdownChip } from '@/components/ui/CountdownChip';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { KpiTile } from '@/components/ui/KpiTile';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { SkeletonLines } from '@/components/ui/Skeleton';
import { StatusPill } from '@/components/ui/StatusPill';
import { Timeline } from '@/components/ui/Timeline';
import { useOverview } from '@/features/overview/hooks';
import { formatCutoffLocal, formatDurationMinutes, formatUtcDateWithWeekday } from '@/lib/dates';
import { formatInteger, pluralize } from '@/lib/format';
import { formatUsdCompact } from '@/lib/money';
import { useScenario } from '@/lib/scenario';
import type { SettlementWindow } from '@/types/api';
import { RAIL_LABELS } from '@/types/domain';

const WINDOW_COLUMNS: DataTableColumn<SettlementWindow>[] = [
  {
    id: 'rail',
    header: 'Rail',
    cell: (w) => (
      <span className="font-medium text-navy-900">
        {RAIL_LABELS[w.rail] ?? w.rail} <span className="text-slate-400">· {w.currency}</span>
      </span>
    ),
  },
  {
    id: 'cutoff',
    header: 'Cutoff',
    cell: (w) => (
      <span className="tnum">
        {formatCutoffLocal(w.cutoff_local, w.timezone)}
        <span className="block text-[11px] text-slate-500">
          <DateTime value={w.cutoff_at} mode="time" />
        </span>
      </span>
    ),
  },
  {
    id: 'status',
    header: 'Status',
    cell: (w) => <StatusPill kind="window" status={w.status} size="sm" />,
  },
  {
    id: 'remaining',
    header: 'Remaining',
    cell: (w) =>
      w.status === 'CLOSED' ? (
        <span className="text-slate-400">
          Rolled to {w.next_window_key.split(':')[1] ?? w.next_window_key}
        </span>
      ) : (
        <CountdownChip dueBy={w.cutoff_at} size="sm" prefix="Closes in" />
      ),
  },
  {
    id: 'pending',
    header: 'Pending',
    align: 'right',
    cell: (w) => <span className="tnum">{formatInteger(w.pending_count)}</span>,
  },
  {
    id: 'value',
    header: 'Pending value',
    align: 'right',
    cell: (w) => <Money amount={w.pending_value} currency={w.currency} muteCode />,
  },
];

function severityBreakdown(bySeverity: Partial<Record<string, number>>): string {
  const parts = (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const)
    .filter((key) => (bySeverity[key] ?? 0) > 0)
    .map((key) => `${bySeverity[key]} ${key.toLowerCase()}`);
  return parts.length ? parts.join(' · ') : 'No open exceptions';
}

export default function OverviewPage() {
  const scenario = useScenario();
  const overview = useOverview();
  const data = overview.data;
  const loading = overview.isPending;

  const dayLabel =
    scenario.data?.business_day_label ?? (data ? formatUtcDateWithWeekday(data.date) : '');

  return (
    <div className="space-y-5">
      <PageHeader
        title="Operations overview"
        description={
          dayLabel
            ? `Processing, settlement and exception posture for ${dayLabel}. Values in USD use scenario reference rates.`
            : 'Processing, settlement and exception posture for the current business day.'
        }
      />

      {overview.isError ? (
        <Card>
          <ErrorState
            error={overview.error}
            onRetry={() => void overview.refetch()}
            retrying={overview.isRefetching}
          />
        </Card>
      ) : (
        <>
          <div
            className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-5"
            data-testid="overview-kpis"
          >
            <KpiTile
              label="Processed today"
              value={formatInteger(data?.processed_count)}
              subtext={
                data
                  ? `${formatUsdCompact(data.processed_value_usd)} across ${data.processed_value_by_currency.length} currencies`
                  : undefined
              }
              icon={ArrowLeftRight}
              to="/payments"
              isLoading={loading}
            />
            <KpiTile
              label="Processed value"
              value={formatUsdCompact(data?.processed_value_usd)}
              subtext="USD equivalent · scenario rates"
              icon={Wallet}
              iconTone="teal"
              isLoading={loading}
            />
            <KpiTile
              label="Pending settlement"
              value={formatUsdCompact(data?.pending_settlement_value_usd)}
              subtext={
                data
                  ? pluralize(data.pending_settlement_count, 'payment') + ' awaiting settlement'
                  : undefined
              }
              icon={Hourglass}
              iconTone="info"
              to="/settlement"
              isLoading={loading}
            />
            <KpiTile
              label="Open exceptions"
              value={formatInteger(data?.exceptions_open_count)}
              subtext={data ? severityBreakdown(data.exceptions_by_severity) : undefined}
              subtextTone={
                data && (data.exceptions_by_severity.CRITICAL ?? 0) > 0 ? 'danger' : 'neutral'
              }
              icon={AlertTriangle}
              iconTone="warning"
              to="/exceptions"
              isLoading={loading}
            />
            <KpiTile
              label="High-priority issues"
              value={formatInteger(data?.high_priority_issue_count)}
              subtext={
                data
                  ? `${data.high_priority_items.filter((i) => i.kind === 'INCIDENT').length} incidents · ${data.high_priority_items.filter((i) => i.kind === 'EXCEPTION').length} exceptions`
                  : undefined
              }
              subtextTone={data && data.high_priority_issue_count > 0 ? 'warning' : 'neutral'}
              icon={Flame}
              iconTone="danger"
              isLoading={loading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
            <Card className="xl:col-span-3" data-testid="overview-settlement-windows">
              <CardHeader>
                <div>
                  <CardTitle>Settlement windows</CardTitle>
                  <CardDescription>
                    Cutoffs in each rail&apos;s business timezone, evaluated at scenario time.
                  </CardDescription>
                </div>
                <Link
                  to="/settlement"
                  className="text-xs font-medium text-teal-700 hover:underline"
                >
                  View batches
                </Link>
              </CardHeader>
              <DataTable
                aria-label="Settlement windows"
                columns={WINDOW_COLUMNS}
                rows={data?.settlement_windows ?? []}
                rowKey={(w) => `${w.rail}:${w.cutoff_at}`}
                isLoading={loading}
                skeletonRows={6}
                stickyHeader={false}
                emptyState={<EmptyState title="No settlement windows" size="sm" />}
              />
            </Card>

            <Card className="xl:col-span-2" data-testid="overview-high-priority">
              <CardHeader>
                <div>
                  <CardTitle>Needs attention</CardTitle>
                  <CardDescription>
                    Open incidents and exceptions closest to breaching their SLA.
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-5">
                    <SkeletonLines lines={5} />
                  </div>
                ) : !data || data.high_priority_items.length === 0 ? (
                  <EmptyState
                    title="Nothing urgent"
                    description="No high-priority exceptions or incidents right now."
                    size="sm"
                  />
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {data.high_priority_items.map((item) => (
                      <li key={`${item.kind}-${item.ref}`}>
                        <Link
                          to={item.href}
                          className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-slate-50 focus-visible:bg-teal-50"
                        >
                          <Badge
                            tone={item.kind === 'INCIDENT' ? 'danger' : 'navy'}
                            size="sm"
                            uppercase
                            className="mt-0.5 shrink-0"
                          >
                            {item.kind === 'INCIDENT' ? 'Incident' : 'Exception'}
                          </Badge>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-13 font-medium text-navy-900">
                              <span className="font-mono text-xs text-teal-700">{item.ref}</span>
                              <span className="mx-1.5 text-slate-300">·</span>
                              {item.title}
                            </p>
                            <div className="mt-1 flex flex-wrap items-center gap-1.5">
                              <SeverityBadge severity={item.severity} />
                              {item.due_by && <CountdownChip dueBy={item.due_by} size="sm" />}
                            </div>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
            <Card className="xl:col-span-3" data-testid="overview-recent-events">
              <CardHeader>
                <div>
                  <CardTitle>Recent activity</CardTitle>
                  <CardDescription>
                    Latest audit events across payments, exceptions, approvals and settlement.
                  </CardDescription>
                </div>
                <Link to="/audit" className="text-xs font-medium text-teal-700 hover:underline">
                  Open audit log
                </Link>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <SkeletonLines lines={6} />
                ) : (
                  <Timeline
                    dense
                    items={(data?.recent_events ?? []).map((event) => ({
                      id: event.event_id,
                      occurredAt: event.occurred_at,
                      kind: 'AUDIT',
                      title: event.summary,
                      detail: (
                        <span className="font-mono text-[11px] text-slate-500">
                          {event.action} · {event.entity_type} {event.entity_ref}
                        </span>
                      ),
                      actor: event.actor,
                    }))}
                  />
                )}
              </CardContent>
            </Card>

            <Card className="xl:col-span-2" data-testid="overview-by-currency">
              <CardHeader>
                <div>
                  <CardTitle>Processed by currency</CardTitle>
                  <CardDescription>
                    Today&apos;s processed volume in instructed currency.
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-5">
                    <SkeletonLines lines={4} />
                  </div>
                ) : !data || data.processed_value_by_currency.length === 0 ? (
                  <EmptyState title="No processed payments" size="sm" />
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {data.processed_value_by_currency.map((row) => (
                      <li
                        key={row.currency}
                        className="flex items-center justify-between px-5 py-2.5 text-13"
                      >
                        <span className="font-medium text-navy-900">{row.currency}</span>
                        <span className="text-slate-500">{pluralize(row.count, 'payment')}</span>
                        <Money
                          amount={row.amount}
                          currency={row.currency}
                          muteCode
                          className="font-medium"
                        />
                      </li>
                    ))}
                  </ul>
                )}
                {data && data.trend.length > 0 && (
                  <p className="border-t border-slate-100 px-5 py-2.5 text-[11px] text-slate-500">
                    {data.trend.length}-day trend available · latest day{' '}
                    {formatInteger(data.trend[data.trend.length - 1]?.count)} payments,{' '}
                    {formatInteger(data.trend[data.trend.length - 1]?.exception_count)} exceptions
                    {data.settlement_windows.some((w) => w.status === 'CLOSING_SOON') &&
                      ` · a window closes within ${formatDurationMinutes(Math.min(...data.settlement_windows.filter((w) => w.status === 'CLOSING_SOON').map((w) => w.minutes_to_cutoff ?? 0)))}`}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
