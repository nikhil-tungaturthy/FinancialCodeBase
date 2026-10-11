import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StatusPill } from '@/components/ui/StatusPill';

describe('StatusPill', () => {
  it.each([
    ['payment', 'PENDING_SETTLEMENT', 'Pending settlement'],
    ['payment', 'HELD', 'Held'],
    ['exception', 'IN_REVIEW', 'In review'],
    ['exception', 'PENDING_APPROVAL', 'Pending approval'],
    ['batch', 'DISCREPANCY', 'Discrepancy'],
    ['approval', 'EXPIRED', 'Expired'],
    ['reconciliation', 'NOT_RUN', 'Not run'],
    ['settlement-entry', 'RETURNED', 'Returned'],
    ['window', 'CLOSING_SOON', 'Closing soon'],
  ] as const)('maps %s/%s to the label "%s"', (kind, status, label) => {
    render(<StatusPill kind={kind} status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('applies a semantic tone and renders a status dot', () => {
    const { container } = render(<StatusPill kind="payment" status="FAILED" />);
    const pill = container.firstElementChild as HTMLElement;
    expect(pill.className).toContain('bg-red-100');
    expect(pill.querySelector('[aria-hidden="true"]')).not.toBeNull();
    expect(pill).toHaveAttribute('data-status', 'FAILED');
  });

  it('falls back to a humanised neutral label for unknown values', () => {
    const { container } = render(<StatusPill kind="exception" status="AWAITING_CALLBACK" />);
    expect(screen.getByText('Awaiting Callback')).toBeInTheDocument();
    expect((container.firstElementChild as HTMLElement).className).toContain('bg-slate-100');
  });
});
