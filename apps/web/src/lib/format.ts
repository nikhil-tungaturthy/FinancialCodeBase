/** General-purpose formatting helpers that are neither money nor dates. */

const INTEGER = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 });

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return INTEGER.format(value);
}

/** `0.79` → `79.0%` */
export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return PERCENT.format(value);
}

/** Basis points → `0.50 bps` */
export function formatBps(bps: number | null | undefined): string {
  if (bps === null || bps === undefined) return '—';
  return `${bps} bps`;
}

/** Render `null`/`undefined`/empty as an em dash. */
export function orDash(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const text = String(value).trim();
  return text ? text : '—';
}

/** Truncate long free text for table cells, preserving whole words where possible. */
export function truncate(text: string | null | undefined, max = 80): string {
  if (!text) return '';
  if (text.length <= max) return text;
  const cut = text.slice(0, max - 1);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}

/** `ab12cd34…` for hashes and long identifiers. */
export function shortId(value: string | null | undefined, keep = 8): string {
  if (!value) return '—';
  return value.length <= keep ? value : `${value.slice(0, keep)}…`;
}

/** `priya.raman` → `Priya Raman` when a display name is not available. */
export function displayNameFromUsername(username: string | null | undefined): string {
  if (!username) return '—';
  if (username === 'system') return 'System';
  return username
    .split('.')
    .map((part) => (part ? part[0]!.toUpperCase() + part.slice(1) : part))
    .join(' ');
}

/** Initials for avatars: `Priya Raman` → `PR`. */
export function initials(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?';
}

/** Pluralise with a count: `pluralize(3, 'exception')` → `3 exceptions`. */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatInteger(count)} ${count === 1 ? singular : plural}`;
}

/** Country code → flag-free label (ISO2 shown as-is; keeps tables compact). */
export function countryLabel(iso2: string | null | undefined): string {
  return iso2 ? iso2.toUpperCase() : '—';
}
