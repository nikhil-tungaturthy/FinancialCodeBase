import { Badge, type BadgeProps } from '@/components/ui/Badge';
import {
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_TONES,
  BATCH_STATUS_LABELS,
  BATCH_STATUS_TONES,
  EXCEPTION_STATUS_LABELS,
  EXCEPTION_STATUS_TONES,
  humanize,
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUS_TONES,
  RECONCILIATION_STATUS_LABELS,
  RECONCILIATION_STATUS_TONES,
  SETTLEMENT_ENTRY_STATUS_LABELS,
  SETTLEMENT_ENTRY_STATUS_TONES,
  WINDOW_STATUS_TONES,
  type Tone,
} from '@/types/domain';

export type StatusKind =
  'payment' | 'exception' | 'batch' | 'approval' | 'settlement-entry' | 'reconciliation' | 'window';

const REGISTRY: Record<
  StatusKind,
  { labels: Record<string, string>; tones: Record<string, Tone> }
> = {
  payment: { labels: PAYMENT_STATUS_LABELS, tones: PAYMENT_STATUS_TONES },
  exception: { labels: EXCEPTION_STATUS_LABELS, tones: EXCEPTION_STATUS_TONES },
  batch: { labels: BATCH_STATUS_LABELS, tones: BATCH_STATUS_TONES },
  approval: { labels: APPROVAL_STATUS_LABELS, tones: APPROVAL_STATUS_TONES },
  'settlement-entry': {
    labels: SETTLEMENT_ENTRY_STATUS_LABELS,
    tones: SETTLEMENT_ENTRY_STATUS_TONES,
  },
  reconciliation: { labels: RECONCILIATION_STATUS_LABELS, tones: RECONCILIATION_STATUS_TONES },
  window: {
    labels: { OPEN: 'Open', CLOSED: 'Closed', CLOSING_SOON: 'Closing soon' },
    tones: WINDOW_STATUS_TONES,
  },
};

export interface StatusPillProps extends Omit<BadgeProps, 'tone' | 'children'> {
  kind: StatusKind;
  status: string;
}

/**
 * Status indicator with a coloured dot. Unknown values (new enum members the
 * UI has not caught up with) fall back to a neutral humanised label rather
 * than failing to render.
 */
export function StatusPill({ kind, status, size = 'md', ...props }: StatusPillProps) {
  const registry = REGISTRY[kind];
  const label = registry.labels[status] ?? humanize(status);
  const tone = registry.tones[status] ?? 'neutral';
  return (
    <Badge tone={tone} dot size={size} data-status={status} data-kind={kind} {...props}>
      {label}
    </Badge>
  );
}
