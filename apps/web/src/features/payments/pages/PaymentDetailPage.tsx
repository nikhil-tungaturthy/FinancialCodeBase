import { FileSearch } from 'lucide-react';
import { Link, useParams } from 'react-router';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { CountdownChip } from '@/components/ui/CountdownChip';
import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { KeyValueList } from '@/components/ui/KeyValueList';
import { Money } from '@/components/ui/Money';
import { PageHeader } from '@/components/ui/PageHeader';
import { RefLink } from '@/components/ui/RefLink';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton, SkeletonLines } from '@/components/ui/Skeleton';
import { StatusPill } from '@/components/ui/StatusPill';
import { Timeline } from '@/components/ui/Timeline';
import { usePayment } from '@/features/payments/hooks';
import { ApiError } from '@/lib/api-client';
import { formatCutoffLocal } from '@/lib/dates';
import { countryLabel, orDash } from '@/lib/format';
import {
  CHANNEL_LABELS,
  PRIORITY_LABELS,
  PRIORITY_TONES,
  RAIL_LABELS,
  RISK_TIER_LABELS,
  RISK_TIER_TONES,
  SEGMENT_LABELS,
  humanize,
} from '@/types/domain';

function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <Skeleton className="h-7 w-64" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }, (_, i) => (
          <Card key={i}>
            <CardContent>
              <SkeletonLines lines={5} />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function PaymentDetailPage() {
  const { paymentRef } = useParams<{ paymentRef: string }>();
  const query = usePayment(paymentRef);

  if (query.isPending) return <DetailSkeleton />;

  if (query.isError) {
    if (query.error instanceof ApiError && query.error.isNotFound) {
      return (
        <Card className="mx-auto max-w-lg">
          <EmptyState
            icon={FileSearch}
            title="Payment not found"
            description={
              <>
                No payment with reference{' '}
                <code className="rounded bg-slate-100 px-1">{paymentRef}</code> exists in this
                environment.
              </>
            }
            action={
              <Button asChild variant="outline">
                <Link to="/payments">Back to payments</Link>
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

  const detail = query.data;
  const {
    payment,
    customer,
    debit_account: debitAccount,
    beneficiary,
    instruction,
    fee,
    settlement,
    exception,
  } = detail;

  return (
    <div className="space-y-4" data-testid="payment-detail">
      <PageHeader
        eyebrow="Payment"
        breadcrumbs={[{ label: 'Payments', to: '/payments' }, { label: payment.payment_ref }]}
        title={<span className="font-mono">{payment.payment_ref}</span>}
        meta={
          <>
            <StatusPill kind="payment" status={payment.status} />
            <Badge tone={PRIORITY_TONES[payment.priority]}>
              {PRIORITY_LABELS[payment.priority] ?? payment.priority}
            </Badge>
            <Badge
              tone={RISK_TIER_TONES[payment.risk_tier]}
              title={`Risk score ${payment.risk_score}`}
            >
              {RISK_TIER_LABELS[payment.risk_tier] ?? payment.risk_tier} · {payment.risk_score}
            </Badge>
          </>
        }
        description={
          <>
            {customer.name} → {beneficiary.name} · {RAIL_LABELS[payment.rail] ?? payment.rail} ·{' '}
            <Money
              amount={payment.amount}
              currency={payment.currency}
              className="font-medium text-navy-900"
            />
          </>
        }
      />

      {exception && (
        <Card
          className="border-amber-500/40 bg-amber-100/30"
          data-testid="payment-exception-banner"
        >
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="flex flex-wrap items-center gap-2 text-13">
              <SeverityBadge severity={exception.severity} />
              <span className="font-medium text-navy-900">{exception.reason_title}</span>
              <span className="text-slate-500">({exception.reason_code})</span>
              <StatusPill kind="exception" status={exception.status} size="sm" />
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to={`/exceptions/${exception.exception_ref}`}>
                Open {exception.exception_ref}
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Instruction</CardTitle>
              <CardDescription>Amounts, references and timing as received.</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <KeyValueList
              items={[
                {
                  label: 'Amount',
                  value: (
                    <Money
                      amount={payment.amount}
                      currency={payment.currency}
                      className="text-sm font-semibold text-navy-900"
                    />
                  ),
                },
                {
                  label: 'USD equivalent',
                  value: <Money amount={payment.usd_equivalent} currency="USD" />,
                  hint: 'Scenario reference rate',
                },
                {
                  label: 'Fee',
                  value: <Money amount={fee.amount} currency={fee.currency} />,
                  hint:
                    fee.source === 'LEGACY_FEECALC01' ? 'Legacy FEECALC01' : 'Modern fee schedule',
                },
                { label: 'Rail', value: RAIL_LABELS[payment.rail] ?? payment.rail },
                { label: 'Channel', value: CHANNEL_LABELS[payment.channel] ?? payment.channel },
                { label: 'Purpose code', value: orDash(payment.purpose_code), mono: true },
                {
                  label: 'Requested value date',
                  value: <DateTime value={payment.requested_value_date} mode="date" />,
                },
                { label: 'Value date', value: <DateTime value={payment.value_date} mode="date" /> },
                { label: 'End-to-end reference', value: payment.end_to_end_reference, mono: true },
                {
                  label: 'Remittance information',
                  value: payment.remittance_info,
                  fullWidth: true,
                },
                { label: 'Received', value: <DateTime value={instruction.received_at} /> },
                { label: 'Submitted by', value: instruction.submitted_by },
                { label: 'Created', value: <DateTime value={payment.created_at} /> },
                { label: 'Last updated', value: <DateTime value={payment.updated_at} /> },
                {
                  label: 'Correlation ID',
                  value: payment.correlation_id,
                  mono: true,
                  fullWidth: true,
                },
                ...(payment.failure_reason
                  ? [{ label: 'Failure reason', value: payment.failure_reason, fullWidth: true }]
                  : []),
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Parties</CardTitle>
              <CardDescription>
                Ordering customer, debit account and registered beneficiary.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <KeyValueList
              items={[
                {
                  label: 'Customer',
                  value: customer.name,
                  hint: `${customer.ref} · ${SEGMENT_LABELS[customer.segment] ?? customer.segment} · ${countryLabel(customer.country)}`,
                },
                {
                  label: 'Debit account',
                  value: debitAccount.masked_identifier,
                  mono: true,
                  hint: `${debitAccount.ref} · ${debitAccount.currency} ${humanize(debitAccount.account_type)}`,
                },
                {
                  label: 'Registered beneficiary',
                  value: beneficiary.name,
                  hint: `${beneficiary.ref} · ${countryLabel(beneficiary.country)}`,
                },
                {
                  label: 'Beneficiary account',
                  value: beneficiary.masked_identifier,
                  mono: true,
                  hint: beneficiary.bank_name,
                },
                { label: 'Beneficiary BIC', value: orDash(beneficiary.bic), mono: true },
                {
                  label: 'Verification',
                  value: (
                    <Badge
                      tone={
                        beneficiary.verification_status === 'VERIFIED'
                          ? 'success'
                          : beneficiary.verification_status === 'NAME_MISMATCH_FLAGGED'
                            ? 'danger'
                            : 'warning'
                      }
                      size="sm"
                    >
                      {humanize(beneficiary.verification_status)}
                    </Badge>
                  ),
                },
                {
                  label: 'Instructed beneficiary name',
                  value: instruction.instructed_beneficiary_name,
                  fullWidth: true,
                },
                {
                  label: 'Instructed identifier',
                  value: instruction.instructed_identifier,
                  mono: true,
                },
                { label: 'Instructed BIC', value: orDash(instruction.instructed_bic), mono: true },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Settlement</CardTitle>
              <CardDescription>
                Window assignment in the rail&apos;s business timezone.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <KeyValueList
              items={[
                { label: 'Window', value: orDash(settlement.window_key), mono: true },
                {
                  label: 'Cutoff',
                  value: settlement.cutoff_at ? <DateTime value={settlement.cutoff_at} /> : null,
                  hint: formatCutoffLocal(settlement.cutoff_local_label, settlement.timezone),
                },
                {
                  label: 'Time to cutoff',
                  value: settlement.cutoff_at ? (
                    <CountdownChip dueBy={settlement.cutoff_at} size="sm" prefix="Closes in" />
                  ) : null,
                },
                {
                  label: 'Value date',
                  value: settlement.value_date ? (
                    <DateTime value={settlement.value_date} mode="date" />
                  ) : null,
                },
                {
                  label: 'Batch',
                  value: settlement.batch_ref ? (
                    <RefLink to={`/settlement/batches/${settlement.batch_ref}`}>
                      {settlement.batch_ref}
                    </RefLink>
                  ) : null,
                },
                {
                  label: 'Batch status',
                  value: settlement.batch_status ? (
                    <StatusPill kind="batch" status={settlement.batch_status} size="sm" />
                  ) : null,
                },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Validation</CardTitle>
              <CardDescription>
                {detail.validation_results.length} rules evaluated ·{' '}
                {detail.validation_results.filter((r) => r.outcome === 'FAIL').length} failed ·{' '}
                {detail.validation_results.filter((r) => r.outcome === 'WARN').length} warnings
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {detail.validation_results.length === 0 ? (
              <EmptyState title="Not yet validated" size="sm" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {detail.validation_results.map((result) => (
                  <li key={result.rule_code} className="flex items-start gap-3 px-5 py-2.5 text-13">
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
                    <div className="min-w-0 flex-1">
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
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Activity</CardTitle>
            <CardDescription>Lifecycle events recorded for this payment.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <Timeline
            dense
            items={detail.events.map((event) => ({
              id: String(event.sequence),
              occurredAt: event.occurred_at,
              kind: 'PAYMENT_EVENT',
              title: event.summary,
              detail: event.event_type,
              actor: event.actor,
            }))}
          />
        </CardContent>
      </Card>
    </div>
  );
}
