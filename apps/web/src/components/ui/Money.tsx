import type { ComponentPropsWithRef } from 'react';

import { cn } from '@/lib/cn';
import { amountSign, formatMoney, type FormatMoneyOptions } from '@/lib/money';

export interface MoneyProps
  extends Omit<ComponentPropsWithRef<'span'>, 'children'>, FormatMoneyOptions {
  /** Decimal string from the API, e.g. `"480000.00"`. */
  amount: string | number | null | undefined;
  currency: string;
  /** Colour negative values red and positive values green (for variances). */
  colorBySign?: boolean;
  /** Visually de-emphasise the currency code. */
  muteCode?: boolean;
}

/**
 * Renders a monetary amount with tabular figures and the currency's minor
 * units (JPY 0dp, USD 2dp…). The amount is never converted for arithmetic —
 * only formatted for display.
 */
export function Money({
  amount,
  currency,
  withCode = true,
  compact = false,
  signed = false,
  colorBySign = false,
  muteCode = false,
  className,
  ...props
}: MoneyProps) {
  const sign = amountSign(typeof amount === 'number' ? String(amount) : amount);
  const number = formatMoney(amount, currency, { withCode: false, compact, signed });
  const full = formatMoney(amount, currency, { withCode: true });
  return (
    <span
      className={cn(
        'tnum whitespace-nowrap',
        colorBySign && sign < 0 && 'text-red-600',
        colorBySign && sign > 0 && 'text-green-600',
        className,
      )}
      title={full}
      data-currency={currency}
      {...props}
    >
      {number}
      {withCode && number !== '—' && (
        <>
          {' '}
          <span className={cn(muteCode && 'text-slate-400')}>{currency}</span>
        </>
      )}
    </span>
  );
}
