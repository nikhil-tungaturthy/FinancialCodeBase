import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DataTable, type DataTableColumn } from '@/components/ui/DataTable';

interface Row {
  ref: string;
  amount: number;
  customer: string;
}

const ROWS: Row[] = [
  { ref: 'MGB-PAY-1042', amount: 480000, customer: 'Halvorsen Maritime' },
  { ref: 'MGB-PAY-2287', amount: 140000, customer: 'Kestrel Energy' },
  { ref: 'MGB-PAY-5143', amount: 18450, customer: 'Castellano Olive' },
];

const COLUMNS: DataTableColumn<Row>[] = [
  { id: 'ref', header: 'Payment', cell: (r) => r.ref, sortable: true, sortValue: (r) => r.ref },
  {
    id: 'amount',
    header: 'Amount',
    cell: (r) => r.amount.toString(),
    sortable: true,
    sortValue: (r) => r.amount,
    align: 'right',
  },
  { id: 'customer', header: 'Customer', cell: (r) => r.customer },
];

function bodyRefs() {
  const rows = within(screen.getByRole('table')).getAllByRole('row').slice(1);
  return rows.map((row) => within(row).getAllByRole('cell')[0]!.textContent);
}

describe('DataTable', () => {
  it('sorts client-side and toggles aria-sort on the header', async () => {
    const user = userEvent.setup();
    render(<DataTable aria-label="Payments" columns={COLUMNS} rows={ROWS} rowKey={(r) => r.ref} />);

    const amountHeader = screen.getByRole('columnheader', { name: /amount/i });
    expect(amountHeader).toHaveAttribute('aria-sort', 'none');

    await user.click(within(amountHeader).getByRole('button'));
    expect(amountHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(bodyRefs()).toEqual(['MGB-PAY-5143', 'MGB-PAY-2287', 'MGB-PAY-1042']);

    await user.click(within(amountHeader).getByRole('button'));
    expect(amountHeader).toHaveAttribute('aria-sort', 'descending');
    expect(bodyRefs()).toEqual(['MGB-PAY-1042', 'MGB-PAY-2287', 'MGB-PAY-5143']);

    expect(screen.getByRole('columnheader', { name: /customer/i })).not.toHaveAttribute(
      'aria-sort',
    );
  });

  it('delegates sorting to the parent when controlled', async () => {
    const user = userEvent.setup();
    const onSortChange = vi.fn();
    render(
      <DataTable
        aria-label="Payments"
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.ref}
        sort={{ column: 'ref', direction: 'asc' }}
        onSortChange={onSortChange}
      />,
    );
    await user.click(
      within(screen.getByRole('columnheader', { name: /payment/i })).getByRole('button'),
    );
    expect(onSortChange).toHaveBeenCalledWith({ column: 'ref', direction: 'desc' });
    // Rows are rendered in the order given (server sorted), not re-sorted locally.
    expect(bodyRefs()).toEqual(['MGB-PAY-1042', 'MGB-PAY-2287', 'MGB-PAY-5143']);
  });

  it('activates rows with click, Enter and Space, and marks the selected row', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn();
    render(
      <DataTable
        aria-label="Payments"
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.ref}
        onRowClick={onRowClick}
        selectedRowKey="MGB-PAY-2287"
      />,
    );
    const rows = within(screen.getByRole('table')).getAllByRole('row').slice(1);
    expect(rows[1]).toHaveAttribute('aria-selected', 'true');
    expect(rows[0]).toHaveAttribute('aria-selected', 'false');
    expect(rows[0]).toHaveAttribute('tabindex', '0');

    await user.click(rows[0]!);
    expect(onRowClick).toHaveBeenLastCalledWith(ROWS[0]);

    rows[1]!.focus();
    await user.keyboard('{Enter}');
    expect(onRowClick).toHaveBeenLastCalledWith(ROWS[1]);

    rows[2]!.focus();
    await user.keyboard(' ');
    expect(onRowClick).toHaveBeenLastCalledWith(ROWS[2]);
    expect(onRowClick).toHaveBeenCalledTimes(3);
  });

  it('renders skeleton rows while loading and an empty state when there are no rows', () => {
    const { rerender } = render(
      <DataTable
        aria-label="Payments"
        columns={COLUMNS}
        rows={[]}
        rowKey={(r) => r.ref}
        isLoading
        skeletonRows={3}
      />,
    );
    expect(screen.getByRole('table')).toHaveAttribute('aria-busy', 'true');
    expect(within(screen.getByRole('table')).getAllByRole('row', { hidden: true })).toHaveLength(4);
    expect(screen.queryByText('Nothing to show')).not.toBeInTheDocument();

    rerender(<DataTable aria-label="Payments" columns={COLUMNS} rows={[]} rowKey={(r) => r.ref} />);
    expect(screen.getByText('Nothing to show')).toBeInTheDocument();
  });
});
