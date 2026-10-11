import { act, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CountdownChip } from '@/components/ui/CountdownChip';
import { computeCountdown } from '@/lib/countdown';
import { DEFAULT_SCENARIO_NOW_ISO, setScenarioNow } from '@/lib/scenario';
import { renderWithProviders } from '@/test/render';

const NOW = '2026-03-18T18:40:00Z';

describe('CountdownChip', () => {
  it('shows amber "Due in" when less than two hours remain', () => {
    render(<CountdownChip dueBy="2026-03-18T20:30:00Z" now={NOW} data-testid="chip" />);
    const chip = screen.getByTestId('chip');
    expect(chip).toHaveTextContent('Due in 1h 50m');
    expect(chip).toHaveAttribute('data-countdown', 'warning');
    expect(chip.className).toContain('bg-amber-100');
  });

  it('shows red "Overdue" once the due time has passed', () => {
    render(<CountdownChip dueBy="2026-03-18T18:28:00Z" now={NOW} data-testid="chip" />);
    const chip = screen.getByTestId('chip');
    expect(chip).toHaveTextContent('Overdue 12m');
    expect(chip).toHaveAttribute('data-countdown', 'danger');
    expect(chip.className).toContain('bg-red-100');
  });

  it('stays slate when more than two hours remain', () => {
    render(<CountdownChip dueBy="2026-03-19T00:00:00Z" now={NOW} data-testid="chip" />);
    const chip = screen.getByTestId('chip');
    expect(chip).toHaveTextContent('Due in 5h 20m');
    expect(chip).toHaveAttribute('data-countdown', 'neutral');
    expect(chip.className).toContain('bg-slate-100');
  });

  it('renders a neutral "No SLA" chip when there is no due time', () => {
    render(<CountdownChip dueBy={null} now={NOW} data-testid="chip" />);
    expect(screen.getByTestId('chip')).toHaveTextContent('No SLA');
    expect(screen.getByTestId('chip')).toHaveAttribute('data-countdown', 'neutral');
  });

  it('falls back to the scenario clock when no "now" is provided and re-renders when it changes', async () => {
    renderWithProviders(<CountdownChip dueBy="2026-03-18T20:30:00Z" data-testid="chip" />);
    expect(await screen.findByText('Due in 1h 50m')).toBeInTheDocument();
    act(() => setScenarioNow('2026-03-18T20:45:00Z'));
    expect(screen.getByText('Overdue 15m')).toBeInTheDocument();
    act(() => setScenarioNow(DEFAULT_SCENARIO_NOW_ISO));
  });

  it('exposes the due instant in the title for hover', () => {
    render(<CountdownChip dueBy="2026-03-18T20:30:00Z" now={NOW} data-testid="chip" />);
    expect(screen.getByTestId('chip')).toHaveAttribute('title', 'Due by 2026-03-18T20:30:00.000Z');
  });
});

describe('computeCountdown', () => {
  it('honours a custom warning window', () => {
    expect(computeCountdown('2026-03-18T19:10:00Z', NOW, 15).tone).toBe('neutral');
    expect(computeCountdown('2026-03-18T18:50:00Z', NOW, 15).tone).toBe('warning');
  });

  it('formats multi-day durations', () => {
    expect(computeCountdown('2026-03-20T20:40:00Z', NOW).label).toBe('Due in 2d 2h');
  });
});
