import { useSearchParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import {
  useBusinessRules,
  useExceptionReasonPolicies,
  useFeeSchedules,
  useSettlementCutoffPolicies,
} from '@/features/policies/hooks';
import { formatDurationMinutes } from '@/lib/dates';
import { formatBps, orDash } from '@/lib/format';
import { formatMoney } from '@/lib/money';
import { useDemoIdentity, useUsers } from '@/lib/identity';
import type {
  BusinessRule,
  FeeSchedule,
  ReasonPolicy,
  SettlementCutoffPolicy,
  User,
} from '@/types/api';
import {
  EXCEPTION_ACTION_LABELS,
  RAIL_LABELS,
  ROLE_LABELS,
  SEGMENT_LABELS,
  humanize,
} from '@/types/domain';

const TABS = [
  'exception-reasons',
  'settlement-cutoffs',
  'business-rules',
  'fee-schedules',
  'demo-identity',
] as const;
type TabKey = (typeof TABS)[number];

const REASON_COLUMNS: DataTableColumn<ReasonPolicy>[] = [
  {
    id: 'code',
    header: 'Reason code',
    width: '230px',
    cell: (r) => (
      <span className="font-mono text-xs font-medium text-navy-900">{r.reason_code}</span>
    ),
  },
  {
    id: 'title',
    header: 'Title',
    cell: (r) => (
      <span className="block max-w-[320px]">
        <span className="block font-medium text-navy-900">{r.title}</span>
        <span className="block text-[11px] leading-relaxed text-slate-500">{r.description}</span>
      </span>
    ),
  },
  {
    id: 'severity',
    header: 'Default severity',
    cell: (r) => <SeverityBadge severity={r.default_severity} />,
  },
  {
    id: 'sla',
    header: 'SLA',
    align: 'right',
    sortable: true,
    sortValue: (r) => r.sla_minutes,
    cell: (r) => <span className="tnum">{formatDurationMinutes(r.sla_minutes)}</span>,
  },
  {
    id: 'approval',
    header: 'Release approval',
    cell: (r) =>
      r.requires_approval_for_release ? (
        <span className="block text-xs">
          <Badge tone="navy" size="sm">
            {r.approval_role
              ? (ROLE_LABELS[r.approval_role] ?? humanize(r.approval_role))
              : 'Required'}
          </Badge>
          {r.approval_amount_threshold_usd && (
            <span className="mt-0.5 block text-slate-500">
              ≥ {formatMoney(r.approval_amount_threshold_usd, 'USD')}
            </span>
          )}
        </span>
      ) : (
        <span className="text-slate-400">Not required</span>
      ),
  },
  {
    id: 'actions',
    header: 'Allowed actions',
    hideBelow: 'xl',
    cell: (r) => (
      <span className="flex flex-wrap gap-1">
        {r.allowed_actions.map((action, index) => (
          <Badge
            key={action}
            tone={index === 0 ? 'teal' : 'neutral'}
            size="sm"
            title={index === 0 ? 'Default action' : undefined}
          >
            {EXCEPTION_ACTION_LABELS[action] ?? humanize(action)}
          </Badge>
        ))}
      </span>
    ),
  },
  {
    id: 'owner',
    header: 'Owner',
    hideBelow: 'lg',
    cell: (r) => (
      <span className="text-slate-700">
        {r.owner_team}
        <span className="block font-mono text-[11px] text-slate-500">{orDash(r.legacy_code)}</span>
      </span>
    ),
  },
];

const CUTOFF_COLUMNS: DataTableColumn<SettlementCutoffPolicy>[] = [
  {
    id: 'rail',
    header: 'Rail',
    cell: (c) => (
      <span className="font-medium text-navy-900">
        {RAIL_LABELS[c.rail] ?? c.rail}
        <span className="block font-mono text-[11px] font-normal text-slate-500">{c.rail}</span>
      </span>
    ),
  },
  {
    id: 'timezone',
    header: 'Business timezone',
    cell: (c) => <span className="font-mono text-xs">{c.timezone}</span>,
  },
  {
    id: 'cutoff',
    header: 'Cutoff (local)',
    cell: (c) => <span className="tnum font-medium">{c.cutoff_local}</span>,
  },
  {
    id: 'offset',
    header: 'Value date offset',
    align: 'right',
    cell: (c) => <span className="tnum">T+{c.value_date_offset_days}</span>,
  },
  {
    id: 'days',
    header: 'Business days',
    hideBelow: 'lg',
    cell: (c) => (
      <span className="text-slate-700">
        {c.business_days.length === 7
          ? 'All days'
          : c.business_days.map((d) => d.slice(0, 3)).join(', ')}
      </span>
    ),
  },
  {
    id: 'holidays',
    header: 'Holidays',
    hideBelow: 'xl',
    cell: (c) =>
      c.holidays.length ? (
        <span className="font-mono text-[11px] text-slate-600">{c.holidays.join(', ')}</span>
      ) : (
        <span className="text-slate-400">None</span>
      ),
  },
];

const RULE_COLUMNS: DataTableColumn<BusinessRule>[] = [
  {
    id: 'code',
    header: 'Rule',
    width: '110px',
    cell: (r) => <span className="font-mono text-xs font-medium text-navy-900">{r.rule_code}</span>,
  },
  {
    id: 'name',
    header: 'Name',
    cell: (r) => (
      <span className="block max-w-[360px]">
        <span className="block font-medium text-navy-900">{r.name}</span>
        <span className="block text-[11px] leading-relaxed text-slate-500">{r.description}</span>
      </span>
    ),
  },
  {
    id: 'category',
    header: 'Category',
    cell: (r) => (
      <Badge tone="neutral" size="sm">
        {humanize(r.category)}
      </Badge>
    ),
  },
  { id: 'severity', header: 'Severity', cell: (r) => <SeverityBadge severity={r.severity} /> },
  {
    id: 'enabled',
    header: 'Enabled',
    cell: (r) => (
      <Badge tone={r.enabled ? 'success' : 'neutral'} size="sm" dot>
        {r.enabled ? 'Enabled' : 'Disabled'}
      </Badge>
    ),
  },
  {
    id: 'owner',
    header: 'Owner',
    hideBelow: 'lg',
    cell: (r) => <span className="text-slate-700">{r.owner_team}</span>,
  },
  {
    id: 'legacy',
    header: 'Legacy origin',
    hideBelow: 'xl',
    cell: (r) =>
      r.legacy_origin ? (
        <Badge tone="warning" size="sm" className="font-mono normal-case">
          {r.legacy_origin}
        </Badge>
      ) : (
        <span className="text-slate-400">—</span>
      ),
  },
];

const FEE_COLUMNS: DataTableColumn<FeeSchedule>[] = [
  {
    id: 'rail',
    header: 'Rail',
    cell: (f) => <span className="font-medium text-navy-900">{RAIL_LABELS[f.rail] ?? f.rail}</span>,
  },
  { id: 'currency', header: 'Currency', cell: (f) => f.currency },
  {
    id: 'segment',
    header: 'Segment',
    cell: (f) => SEGMENT_LABELS[f.segment] ?? humanize(f.segment),
  },
  {
    id: 'type',
    header: 'Type',
    cell: (f) => (
      <Badge tone="neutral" size="sm">
        {f.fee_type === 'FLAT' ? 'Flat' : 'Flat + bps'}
      </Badge>
    ),
  },
  {
    id: 'flat',
    header: 'Flat',
    align: 'right',
    cell: (f) => <Money amount={f.flat_amount} currency={f.currency} muteCode />,
  },
  {
    id: 'bps',
    header: 'Bps',
    align: 'right',
    cell: (f) => <span className="tnum">{f.fee_type === 'FLAT' ? '—' : formatBps(f.bps)}</span>,
  },
  {
    id: 'min',
    header: 'Min',
    align: 'right',
    hideBelow: 'lg',
    cell: (f) => (
      <Money amount={f.min_fee} currency={f.currency} withCode={false} className="text-slate-600" />
    ),
  },
  {
    id: 'max',
    header: 'Max',
    align: 'right',
    hideBelow: 'lg',
    cell: (f) => (
      <Money amount={f.max_fee} currency={f.currency} withCode={false} className="text-slate-600" />
    ),
  },
  {
    id: 'effective',
    header: 'Effective',
    hideBelow: 'xl',
    cell: (f) => (
      <span className="text-xs text-slate-600">
        <DateTime value={f.effective_from} mode="date" />
        {f.effective_to && (
          <>
            {' '}
            → <DateTime value={f.effective_to} mode="date" />
          </>
        )}
      </span>
    ),
  },
  {
    id: 'source',
    header: 'Source',
    cell: (f) => (
      <Badge
        tone={f.source === 'LEGACY_FEECALC01' ? 'warning' : 'teal'}
        size="sm"
        className="font-mono normal-case"
      >
        {f.source}
      </Badge>
    ),
  },
];

const USER_COLUMNS: DataTableColumn<User>[] = [
  {
    id: 'username',
    header: 'Username',
    cell: (u) => <span className="font-mono text-xs font-medium text-navy-900">{u.username}</span>,
  },
  {
    id: 'display',
    header: 'Name',
    cell: (u) => (
      <span className="text-slate-800">
        {u.display_name}
        <span className="block text-[11px] text-slate-500">{u.email}</span>
      </span>
    ),
  },
  {
    id: 'role',
    header: 'Role',
    cell: (u) => (
      <Badge tone="navy" size="sm">
        {ROLE_LABELS[u.role] ?? humanize(u.role)}
      </Badge>
    ),
  },
  { id: 'team', header: 'Team', cell: (u) => <span className="text-slate-700">{u.team}</span> },
  {
    id: 'active',
    header: 'Active',
    cell: (u) => (
      <Badge tone={u.is_active ? 'success' : 'neutral'} size="sm" dot>
        {u.is_active ? 'Active' : 'Inactive'}
      </Badge>
    ),
  },
];

interface PolicyTableProps<T> {
  title: string;
  description: string;
  columns: DataTableColumn<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
  isRefetching: boolean;
  testId: string;
  footer?: React.ReactNode;
  selectedRowKey?: string | null;
}

function PolicyTable<T>({
  title,
  description,
  columns,
  rows,
  rowKey,
  isPending,
  isError,
  error,
  refetch,
  isRefetching,
  testId,
  footer,
  selectedRowKey,
}: PolicyTableProps<T>) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
      </CardHeader>
      {isError ? (
        <ErrorState error={error} onRetry={refetch} retrying={isRefetching} />
      ) : (
        <DataTable
          aria-label={title}
          testId={testId}
          columns={columns}
          rows={rows ?? []}
          rowKey={rowKey}
          isLoading={isPending}
          selectedRowKey={selectedRowKey}
          emptyState={<EmptyState title={`No ${title.toLowerCase()} configured`} size="sm" />}
        />
      )}
      {footer}
    </Card>
  );
}

function DemoIdentityTab() {
  const users = useUsers();
  const current = useDemoIdentity();
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>How demo identity works</CardTitle>
            <CardDescription>
              The console has no login. This is deliberate for the demo and is not production
              authentication.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-13 leading-relaxed text-slate-700">
          <p>
            Every API request carries an{' '}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">X-Demo-User</code>{' '}
            header naming one of the seeded users. The API resolves the user and enforces role
            checks server-side (for example, cancelling a payment requires{' '}
            <strong>Supervisor</strong> or above; approving a release requires the role named by the
            exception policy). A missing header falls back to the default analyst; an unknown
            username returns{' '}
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">401</code>.
          </p>
          <p>
            Use the <strong>Demo identity</strong> switcher in the top bar to act as a different
            user. The selection is stored in your browser (
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs">
              localStorage: mf.demoUser
            </code>
            ) and all data is refetched so role-dependent affordances update immediately. You are
            currently acting as{' '}
            <span className="font-mono text-xs font-semibold text-navy-900">{current}</span>.
          </p>
        </CardContent>
      </Card>
      <PolicyTable<User>
        title="Seeded users"
        description="Identities available to the switcher. Segregation of duties prevents a requester from approving their own request."
        columns={USER_COLUMNS}
        rows={users.data}
        rowKey={(u) => u.username}
        isPending={users.isPending}
        isError={users.isError}
        error={users.error}
        refetch={() => void users.refetch()}
        isRefetching={users.isRefetching}
        testId="policy-users-table"
        selectedRowKey={current}
      />
    </div>
  );
}

export default function PoliciesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get('tab');
  const tab: TabKey = (TABS as readonly string[]).includes(requested ?? '')
    ? (requested as TabKey)
    : 'exception-reasons';

  const reasons = useExceptionReasonPolicies();
  const cutoffs = useSettlementCutoffPolicies();
  const rules = useBusinessRules();
  const fees = useFeeSchedules();

  return (
    <div className="space-y-4">
      <PageHeader
        title="Policies & reference data"
        description="Operating rules the platform enforces: exception handling, settlement cutoffs, validation thresholds and fee schedules."
        meta={
          reasons.data ? (
            <Badge tone="neutral" size="sm">
              Policy version {reasons.data.version}
            </Badge>
          ) : undefined
        }
      />
      <Tabs
        value={tab}
        onValueChange={(value) => {
          const next = new URLSearchParams(searchParams);
          next.set('tab', value);
          setSearchParams(next, { replace: true });
        }}
      >
        <TabsList data-testid="policy-tabs" aria-label="Policy areas">
          <TabsTrigger value="exception-reasons">Exception reasons</TabsTrigger>
          <TabsTrigger value="settlement-cutoffs">Settlement cutoffs</TabsTrigger>
          <TabsTrigger value="business-rules">Business rules</TabsTrigger>
          <TabsTrigger value="fee-schedules">Fee schedules</TabsTrigger>
          <TabsTrigger value="demo-identity">Demo identity</TabsTrigger>
        </TabsList>

        <TabsContent value="exception-reasons">
          <PolicyTable<ReasonPolicy>
            title="Exception reason policies"
            description="Severity, SLA, approval requirements and permitted actions per reason code. The first allowed action is the default."
            columns={REASON_COLUMNS}
            rows={reasons.data?.reasons}
            rowKey={(r) => r.reason_code}
            isPending={reasons.isPending}
            isError={reasons.isError}
            error={reasons.error}
            refetch={() => void reasons.refetch()}
            isRefetching={reasons.isRefetching}
            testId="policy-exception-reasons"
          />
        </TabsContent>
        <TabsContent value="settlement-cutoffs">
          <PolicyTable<SettlementCutoffPolicy>
            title="Settlement cutoffs"
            description="Cutoff time in each rail's business timezone, value-date offset and holiday calendar. Submissions after cutoff roll to the next business day."
            columns={CUTOFF_COLUMNS}
            rows={cutoffs.data}
            rowKey={(c) => c.rail}
            isPending={cutoffs.isPending}
            isError={cutoffs.isError}
            error={cutoffs.error}
            refetch={() => void cutoffs.refetch()}
            isRefetching={cutoffs.isRefetching}
            testId="policy-settlement-cutoffs"
          />
        </TabsContent>
        <TabsContent value="business-rules">
          <PolicyTable<BusinessRule>
            title="Business rules"
            description="Validation, limit, cutoff, screening, fee and approval rules, with their legacy origin where the logic was migrated."
            columns={RULE_COLUMNS}
            rows={rules.data}
            rowKey={(r) => r.rule_code}
            isPending={rules.isPending}
            isError={rules.isError}
            error={rules.error}
            refetch={() => void rules.refetch()}
            isRefetching={rules.isRefetching}
            testId="policy-business-rules"
          />
        </TabsContent>
        <TabsContent value="fee-schedules">
          <PolicyTable<FeeSchedule>
            title="Fee schedules"
            description="Modern fee schedules by rail, currency and segment. USD wire and SWIFT fees are governed by the legacy FEECALC01 reference."
            columns={FEE_COLUMNS}
            rows={fees.data}
            rowKey={(f) => `${f.rail}:${f.currency}:${f.segment}:${f.effective_from}`}
            isPending={fees.isPending}
            isError={fees.isError}
            error={fees.error}
            refetch={() => void fees.refetch()}
            isRefetching={fees.isRefetching}
            testId="policy-fee-schedules"
          />
        </TabsContent>
        <TabsContent value="demo-identity">
          <DemoIdentityTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
