import { Link } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Timeline, type TimelineItem } from '@/components/ui/Timeline';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { CountdownChip } from '@/components/ui/CountdownChip';
import { DateTime } from '@/components/ui/DateTime';
import { KeyValueList } from '@/components/ui/KeyValueList';
import { Money } from '@/components/ui/Money';
import { RefLink } from '@/components/ui/RefLink';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusPill } from '@/components/ui/StatusPill';
import type { ExceptionDetail } from '@/types/api';
import { humanize, PRIORITY_LABELS, PRIORITY_TONES, RAIL_LABELS } from '@/types/domain';

export interface ExceptionDetailPanelProps {
  detail: ExceptionDetail;
}

function toTimeline(detail: ExceptionDetail): TimelineItem[] {
  return detail.timeline.map((entry, index) => ({
    id: `${entry.kind}-${entry.occurred_at}-${index}`,
    occurredAt: entry.occurred_at,
    kind: entry.kind,
    title: entry.title,
    detail: entry.detail,
    actor: entry.actor,
  }));
}

/**
 * Exception workbench detail panel — header and core facts. Review sections
 * are composed here as they are added under `./sections/`.
 */
export function ExceptionDetailPanel({ detail }: ExceptionDetailPanelProps) {
  const { exception, payment } = detail;
  return (
    <Card className="flex min-h-0 flex-1 flex-col" data-testid="exception-detail">
      <CardHeader className="flex-col items-stretch gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-mono text-sm font-semibold text-navy-900">
            {exception.exception_ref}
          </h2>
          <SeverityBadge severity={exception.severity} />
          <StatusPill kind="exception" status={exception.status} size="sm" />
          <CountdownChip dueBy={exception.due_by} size="sm" className="ml-auto" />
        </div>
        <div>
          <p className="text-sm font-medium text-navy-900">{exception.reason_title}</p>
          <p className="text-xs text-slate-500">
            <span className="font-mono">{exception.reason_code}</span> · queue {exception.queue} ·
            opened <DateTime value={exception.opened_at} />
          </p>
        </div>
        {exception.summary && (
          <p className="text-13 leading-relaxed text-slate-700">{exception.summary}</p>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto scrollbar-thin">
        <KeyValueList
          aria-label="Exception facts"
          items={[
            {
              label: 'Payment',
              value: (
                <RefLink to={`/payments/${payment.payment_ref}`}>{payment.payment_ref}</RefLink>
              ),
            },
            {
              label: 'Payment status',
              value: <StatusPill kind="payment" status={payment.status} size="sm" />,
            },
            { label: 'Customer', value: payment.customer_name },
            { label: 'Beneficiary', value: payment.beneficiary_name },
            {
              label: 'Amount',
              value: (
                <Money
                  amount={payment.amount}
                  currency={payment.currency}
                  className="font-medium"
                />
              ),
            },
            { label: 'Rail', value: RAIL_LABELS[payment.rail] ?? payment.rail },
            {
              label: 'Priority',
              value: (
                <Badge tone={PRIORITY_TONES[payment.priority]} size="sm">
                  {PRIORITY_LABELS[payment.priority] ?? payment.priority}
                </Badge>
              ),
            },
            {
              label: 'Assigned to',
              value: exception.assigned_to ? exception.assigned_to.display_name : null,
              hint: exception.assigned_to ? `@${exception.assigned_to.username}` : 'Unassigned',
            },
            { label: 'Due by', value: <DateTime value={exception.due_by} /> },
            { label: 'Correlation ID', value: exception.correlation_id, mono: true },
            ...(exception.resolved_at
              ? [
                  { label: 'Resolved', value: <DateTime value={exception.resolved_at} /> },
                  {
                    label: 'Resolution',
                    value: exception.resolution_code ? humanize(exception.resolution_code) : null,
                  },
                ]
              : []),
          ]}
        />
        <section className="mt-5 border-t border-slate-100 pt-4" aria-label="Validation results">
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            Validation
          </h3>
          {detail.validation_results.length === 0 ? (
            <p className="text-13 text-slate-500">No validation results recorded.</p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
              {detail.validation_results.map((result) => (
                <li key={result.rule_code} className="flex items-start gap-3 px-3 py-2 text-13">
                  <Badge
                    tone={
                      result.outcome === 'PASS'
                        ? 'success'
                        : result.outcome === 'FAIL'
                          ? 'danger'
                          : result.outcome === 'WARN'
                            ? 'warning'
                            : 'neutral'
                    }
                    size="sm"
                    uppercase
                    className="mt-0.5 w-16 shrink-0 justify-center"
                  >
                    {result.outcome}
                  </Badge>
                  <div className="min-w-0">
                    <p className="font-medium text-navy-900">
                      <span className="font-mono text-xs text-slate-500">{result.rule_code}</span>{' '}
                      {result.rule_name}
                    </p>
                    <p className="text-xs text-slate-600">{result.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="mt-5 border-t border-slate-100 pt-4" aria-label="Activity">
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            Activity
          </h3>
          <Timeline dense items={toTimeline(detail)} />
        </section>
        <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          <Button asChild size="sm" variant="outline">
            <Link to={`/payments/${payment.payment_ref}`}>Open payment</Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link to={`/audit?correlation_id=${encodeURIComponent(exception.correlation_id)}`}>
              Audit trail
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
