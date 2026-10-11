import {
  ArrowLeftRight,
  Cpu,
  FileText,
  MessageSquare,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import type { ReactNode } from 'react';

import { DateTime } from '@/components/ui/DateTime';
import { EmptyState } from '@/components/ui/EmptyState';
import { TONE_ICON_BG_CLASSES } from '@/components/ui/tones';
import { cn } from '@/lib/cn';
import { displayNameFromUsername } from '@/lib/format';
import type { Tone } from '@/types/domain';

export type TimelineEntryKind = 'PAYMENT_EVENT' | 'AUDIT' | 'NOTE' | 'EVIDENCE' | 'SYSTEM';

export interface TimelineItem {
  id: string;
  occurredAt: string;
  kind: TimelineEntryKind | string;
  title: ReactNode;
  detail?: ReactNode;
  actor?: string | null;
  tone?: Tone;
}

const KIND_META: Record<TimelineEntryKind, { icon: LucideIcon; tone: Tone; label: string }> = {
  PAYMENT_EVENT: { icon: ArrowLeftRight, tone: 'navy', label: 'Payment event' },
  AUDIT: { icon: ShieldCheck, tone: 'teal', label: 'Audit' },
  NOTE: { icon: MessageSquare, tone: 'info', label: 'Note' },
  EVIDENCE: { icon: FileText, tone: 'warning', label: 'Evidence' },
  SYSTEM: { icon: Cpu, tone: 'neutral', label: 'System' },
};

function metaFor(kind: string) {
  return KIND_META[kind as TimelineEntryKind] ?? KIND_META.SYSTEM;
}

export interface TimelineProps {
  items: ReadonlyArray<TimelineItem>;
  emptyTitle?: string;
  className?: string;
  dense?: boolean;
}

/** Vertical activity timeline with kind-aware icons; newest entry wherever the caller puts it. */
export function Timeline({
  items,
  emptyTitle = 'No activity yet',
  className,
  dense = false,
}: TimelineProps) {
  if (items.length === 0) {
    return <EmptyState title={emptyTitle} size="sm" className={className} />;
  }
  return (
    <ol className={cn('relative', className)} aria-label="Activity timeline">
      {items.map((item, index) => {
        const meta = metaFor(item.kind);
        const Icon = meta.icon;
        const tone = item.tone ?? meta.tone;
        const last = index === items.length - 1;
        return (
          <li
            key={item.id}
            className={cn('relative flex gap-3', dense ? 'pb-4' : 'pb-6', last && 'pb-0')}
          >
            {!last && (
              <span
                aria-hidden="true"
                className="absolute top-7 bottom-0 left-3.5 w-px bg-slate-200"
              />
            )}
            <span
              aria-hidden="true"
              className={cn(
                'relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full ring-4 ring-white [&_svg]:size-3.5',
                TONE_ICON_BG_CLASSES[tone],
              )}
            >
              <Icon />
            </span>
            <div className="min-w-0 flex-1 pt-0.5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <p className="text-13 font-medium text-navy-900">{item.title}</p>
                <DateTime value={item.occurredAt} className="text-xs text-slate-500" />
              </div>
              {item.detail && (
                <div className="mt-1 text-xs leading-relaxed text-slate-600">{item.detail}</div>
              )}
              <p className="mt-1 text-[11px] text-slate-400">
                <span className="sr-only">{meta.label} · </span>
                {item.actor ? displayNameFromUsername(item.actor) : meta.label}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
