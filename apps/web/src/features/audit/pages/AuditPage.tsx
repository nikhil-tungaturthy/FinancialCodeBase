import { Search, X } from 'lucide-react';
import type { FormEvent } from 'react';
import { useSearchParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Input } from '@/components/ui/Input';
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
import { useAuditActions, useAuditEvents } from '@/features/audit/hooks';
import { displayNameFromUsername, truncate } from '@/lib/format';
import { patchParams, readEnum, readInt, readString } from '@/lib/url-state';
import type { AuditEvent, AuditListParams } from '@/types/api';
import { humanize, type AuditEntityType } from '@/types/domain';

const ALL = '__all__';
const ENTITY_TYPES: readonly AuditEntityType[] = [
  'PAYMENT',
  'EXCEPTION',
  'APPROVAL',
  'SETTLEMENT_BATCH',
  'RECONCILIATION',
  'INCIDENT',
  'POLICY',
  'USER',
];

/** Resolve an audit entity to its page in the console, when one exists. */
function entityHref(event: AuditEvent): string | null {
  switch (event.entity_type) {
    case 'PAYMENT':
      return `/payments/${event.entity_ref}`;
    case 'EXCEPTION':
      return `/exceptions/${event.entity_ref}`;
    case 'APPROVAL':
      return `/approvals/${event.entity_ref}`;
    case 'SETTLEMENT_BATCH':
    case 'RECONCILIATION':
      return event.entity_ref.startsWith('SB-') ? `/settlement/batches/${event.entity_ref}` : null;
    default:
      return null;
  }
}

const COLUMNS: DataTableColumn<AuditEvent>[] = [
  {
    id: 'occurred_at',
    header: 'Occurred',
    width: '190px',
    cell: (e) => <DateTime value={e.occurred_at} className="text-slate-700" />,
  },
  {
    id: 'action',
    header: 'Action',
    cell: (e) => (
      <Badge tone="navy" size="sm" className="font-mono normal-case">
        {e.action}
      </Badge>
    ),
  },
  {
    id: 'entity',
    header: 'Entity',
    cell: (e) => {
      const href = entityHref(e);
      return (
        <span className="block">
          {href ? (
            <RefLink to={href}>{e.entity_ref}</RefLink>
          ) : (
            <span className="font-mono text-xs text-slate-700">{e.entity_ref}</span>
          )}
          <span className="block text-[11px] text-slate-500">{humanize(e.entity_type)}</span>
        </span>
      );
    },
  },
  {
    id: 'summary',
    header: 'Summary',
    cell: (e) => (
      <span className="block max-w-[420px] text-slate-700" title={e.summary}>
        {truncate(e.summary, 110)}
      </span>
    ),
  },
  {
    id: 'actor',
    header: 'Actor',
    cell: (e) => (
      <span className="text-slate-700">
        {displayNameFromUsername(e.actor)}
        {e.actor_role && (
          <span className="block text-[11px] text-slate-500">{humanize(e.actor_role)}</span>
        )}
      </span>
    ),
  },
  {
    id: 'source',
    header: 'Source',
    hideBelow: 'xl',
    cell: (e) => <span className="font-mono text-[11px] text-slate-500">{e.source_service}</span>,
  },
  {
    id: 'correlation',
    header: 'Correlation',
    hideBelow: 'lg',
    cell: (e) => (
      <span className="font-mono text-[11px] text-slate-500" title={e.correlation_id}>
        {e.correlation_id}
      </span>
    ),
  },
];

export default function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readInt(searchParams, 'page', 1);
  const pageSize = readInt(searchParams, 'page_size', 50);
  const search = readString(searchParams, 'search');
  const entityType = readEnum(searchParams, 'entity_type', ENTITY_TYPES);
  const action = readString(searchParams, 'action');
  const correlationId = readString(searchParams, 'correlation_id');
  const entityRef = readString(searchParams, 'entity_ref');
  const actor = readString(searchParams, 'actor');

  const params: AuditListParams = {
    page,
    page_size: pageSize,
    search,
    entity_type: entityType,
    action,
    correlation_id: correlationId,
    entity_ref: entityRef,
    actor,
  };
  const query = useAuditEvents(params);
  const actions = useAuditActions();
  const update = (patch: Parameters<typeof patchParams>[1]) =>
    setSearchParams(patchParams(searchParams, patch));
  const onSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get('search');
    update({ search: typeof value === 'string' ? value.trim() : '' });
  };
  const hasFilters = Boolean(search || entityType || action || correlationId || entityRef || actor);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Audit log"
        description="Immutable record of every state change across the platform, correlated end-to-end."
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
              placeholder="Search summary, ref, actor…"
              aria-label="Search audit events"
              leadingIcon={<Search />}
              inputSize="sm"
              className="max-w-md"
            />
            <Button type="submit" variant="outline" size="sm">
              Search
            </Button>
          </form>
          <Select
            value={entityType ?? ALL}
            onValueChange={(value) => update({ entity_type: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-44" aria-label="Filter by entity type">
              <SelectValue placeholder="All entities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All entities</SelectItem>
              {ENTITY_TYPES.map((value) => (
                <SelectItem key={value} value={value}>
                  {humanize(value)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={action ?? ALL}
            onValueChange={(value) => update({ action: value === ALL ? null : value })}
          >
            <SelectTrigger size="sm" className="w-56" aria-label="Filter by action">
              <SelectValue placeholder="All actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All actions</SelectItem>
              {(actions.data ?? (action ? [action] : [])).map((value) => (
                <SelectItem key={value} value={value}>
                  <span className="font-mono text-xs">{value}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(correlationId || entityRef || actor) && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
              {correlationId && (
                <Badge tone="teal" size="sm" className="font-mono normal-case">
                  correlation {correlationId}
                </Badge>
              )}
              {entityRef && (
                <Badge tone="teal" size="sm" className="font-mono normal-case">
                  entity {entityRef}
                </Badge>
              )}
              {actor && (
                <Badge tone="teal" size="sm" className="normal-case">
                  actor {actor}
                </Badge>
              )}
            </div>
          )}
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                update({
                  search: null,
                  entity_type: null,
                  action: null,
                  correlation_id: null,
                  entity_ref: null,
                  actor: null,
                })
              }
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
              aria-label="Audit events"
              testId="audit-table"
              columns={COLUMNS}
              rows={query.data?.items ?? []}
              rowKey={(e) => e.event_id}
              isLoading={query.isPending}
              skeletonRows={12}
              emptyState={
                <EmptyState
                  title={hasFilters ? 'No audit events match' : 'No audit events'}
                  description={
                    hasFilters ? 'Try a broader search or clear the filters.' : undefined
                  }
                  size="sm"
                />
              }
            />
            <Pagination
              page={page}
              pageSize={pageSize}
              total={query.data?.total ?? 0}
              itemLabel="events"
              pageSizeOptions={[50, 100, 200]}
              onPageChange={(next) => update({ page: next })}
              onPageSizeChange={(next) => update({ page_size: next })}
            />
          </>
        )}
      </Card>
    </div>
  );
}
