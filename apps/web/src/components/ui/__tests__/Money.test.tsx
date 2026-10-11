import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Money } from '@/components/ui/Money';
import { formatMoney } from '@/lib/money';

const text = (node: HTMLElement) =>
  node.textContent?.replace(new RegExp(String.fromCharCode(160), 'g'), ' ') ?? '';

describe('Money', () => {
  it('formats USD with two decimals and grouping, keeping the string amount intact', () => {
    render(<Money amount="480000.00" currency="USD" data-testid="m" />);
    expect(text(screen.getByTestId('m'))).toBe('480,000.00 USD');
    expect(screen.getByTestId('m')).toHaveAttribute('title', '480,000.00 USD');
  });

  it('formats JPY with zero decimals', () => {
    render(<Money amount="1250000" currency="JPY" data-testid="m" />);
    expect(text(screen.getByTestId('m'))).toBe('1,250,000 JPY');
  });

  it('rounds display of JPY sub-unit noise away and never shows a decimal point', () => {
    render(<Money amount="1250000.00" currency="JPY" data-testid="m" />);
    expect(text(screen.getByTestId('m'))).toBe('1,250,000 JPY');
  });

  it('omits the code when asked and renders a dash for missing amounts', () => {
    const { rerender } = render(
      <Money amount="18450.00" currency="EUR" withCode={false} data-testid="m" />,
    );
    expect(text(screen.getByTestId('m'))).toBe('18,450.00');
    rerender(<Money amount={null} currency="EUR" data-testid="m" />);
    expect(text(screen.getByTestId('m'))).toBe('—');
  });

  it('colours variances by sign and shows an explicit plus when signed', () => {
    render(<Money amount="18450.00" currency="EUR" signed colorBySign data-testid="m" />);
    const node = screen.getByTestId('m');
    expect(text(node)).toBe('+18,450.00 EUR');
    expect(node.className).toContain('text-green-600');
  });

  it('uses tabular figures', () => {
    render(<Money amount="47.20" currency="USD" data-testid="m" />);
    expect(screen.getByTestId('m').className).toContain('tnum');
  });
});

describe('formatMoney', () => {
  it('respects minor units per currency', () => {
    expect(formatMoney('47.2', 'USD')).toBe('47.20 USD');
    expect(formatMoney('92000', 'CHF')).toBe('92,000.00 CHF');
    expect(formatMoney('5000', 'JPY', { withCode: false })).toBe('5,000');
    expect(formatMoney('-18450.00', 'EUR')).toBe('−18,450.00 EUR');
  });
});
