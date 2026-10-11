import { Badge, type BadgeProps } from '@/components/ui/Badge';
import {
  humanize,
  INCIDENT_SEVERITY_TONES,
  SEVERITY_LABELS,
  SEVERITY_TONES,
  type ExceptionSeverity,
  type IncidentSeverity,
  type Tone,
} from '@/types/domain';

export interface SeverityBadgeProps extends Omit<BadgeProps, 'tone' | 'children'> {
  severity: ExceptionSeverity | IncidentSeverity | string;
}

function resolve(severity: string): { label: string; tone: Tone } {
  if (severity in SEVERITY_LABELS) {
    const key = severity as ExceptionSeverity;
    return { label: SEVERITY_LABELS[key], tone: SEVERITY_TONES[key] };
  }
  if (severity in INCIDENT_SEVERITY_TONES) {
    const key = severity as IncidentSeverity;
    return { label: key, tone: INCIDENT_SEVERITY_TONES[key] };
  }
  return { label: humanize(severity), tone: 'neutral' };
}

export function SeverityBadge({ severity, size = 'sm', ...props }: SeverityBadgeProps) {
  const { label, tone } = resolve(severity);
  return (
    <Badge tone={tone} size={size} uppercase data-severity={severity} {...props}>
      {label}
    </Badge>
  );
}
