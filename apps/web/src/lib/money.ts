import type { Currency } from '@/types/domain';

/** Minor units per currency (SPEC §0.1). Unknown codes default to 2. */
export const MINOR_UNITS: Record<Currency, number> = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  CHF: 2,
  JPY: 0,
  SGD: 2,
};

export const CURRENCY_SYMBOLS: Record<Currency, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  CHF: 'CHF',
  JPY: '¥',
  SGD: 'S$',
};

export function minorUnitsFor(currency: string): number {
  return MINOR_UNITS[currency as Currency] ?? 2;
}

const formatterCache = new Map<string, Intl.NumberFormat>();

function numberFormatter(currency: string, options: { compact?: boolean } = {}): Intl.NumberFormat {
  const digits = minorUnitsFor(currency);
  const key = `${currency}:${options.compact ? 'c' : 'f'}`;
  let formatter = formatterCache.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: options.compact ? 0 : digits,
      maximumFractionDigits: options.compact ? 1 : digits,
      notation: options.compact ? 'compact' : 'standard',
      useGrouping: true,
    });
    formatterCache.set(key, formatter);
  }
  return formatter;
}

/**
 * Parse a decimal string into a number purely for display formatting.
 * Returns `null` for empty / non-numeric input so callers can render a dash.
 */
export function toDisplayNumber(amount: string | number | null | undefined): number | null {
  if (amount === null || amount === undefined) return null;
  if (typeof amount === 'number') return Number.isFinite(amount) ? amount : null;
  const trimmed = amount.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export interface FormatMoneyOptions {
  /** Append the ISO code (`480,000.00 USD`). Default true. */
  withCode?: boolean;
  /** Use compact notation (`480K`). Default false. */
  compact?: boolean;
  /** Prefix positive values with `+` (useful for variances). Default false. */
  signed?: boolean;
}

/** Format a decimal-string amount with the currency's minor units and `tnum`-friendly grouping. */
export function formatMoney(
  amount: string | number | null | undefined,
  currency: string,
  options: FormatMoneyOptions = {},
): string {
  const value = toDisplayNumber(amount);
  if (value === null) return '—';
  const { withCode = true, compact = false, signed = false } = options;
  let text = numberFormatter(currency, { compact }).format(Math.abs(value));
  if (value < 0) text = `−${text}`;
  else if (signed && value > 0) text = `+${text}`;
  return withCode ? `${text} ${currency}` : text;
}

/** Format without the currency code — for table cells where currency is its own column. */
export function formatAmount(amount: string | number | null | undefined, currency: string): string {
  return formatMoney(amount, currency, { withCode: false });
}

/** Format a USD-equivalent figure (scenario reference rates) compactly for KPI tiles. */
export function formatUsdCompact(amount: string | number | null | undefined): string {
  const value = toDisplayNumber(amount);
  if (value === null) return '—';
  return `$${numberFormatter('USD', { compact: true }).format(value)}`;
}

/** True when a decimal string represents zero (any precision). */
export function isZeroAmount(amount: string | null | undefined): boolean {
  const value = toDisplayNumber(amount);
  return value === 0;
}

/** Sign of a decimal string: -1, 0 or 1. */
export function amountSign(amount: string | null | undefined): -1 | 0 | 1 {
  const value = toDisplayNumber(amount);
  if (value === null || value === 0) return 0;
  return value < 0 ? -1 : 1;
}
