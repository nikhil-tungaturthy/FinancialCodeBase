import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { type KeyboardEvent, type ReactNode, useState } from 'react';

import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/cn';

export type SortDirection = 'asc' | 'desc';

export interface SortState {
  column: string;
  direction: SortDirection;
}

export type ColumnAlign = 'left' | 'right' | 'center';

export interface DataTableColumn<T> {
  /** Stable identifier; also the `sort` value sent to the API for controlled sorting. */
  id: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  /** Enables the sortable header button. */
  sortable?: boolean;
  /** Value used for client-side sorting when the table is uncontrolled. */
  sortValue?: (row: T) => string | number | null | undefined;
  align?: ColumnAlign;
  /** CSS width (e.g. `140px`, `18%`). */
  width?: string;
  className?: string;
  headerClassName?: string;
  /** Hide the column below a breakpoint to keep dense tables legible. */
  hideBelow?: 'md' | 'lg' | 'xl';
}

export interface DataTableProps<T> {
  columns: ReadonlyArray<DataTableColumn<T>>;
  rows: ReadonlyArray<T>;
  rowKey: (row: T) => string;
  /** Controlled sort state (server-side sorting). */
  sort?: SortState | null;
  onSortChange?: (next: SortState) => void;
  /** Initial sort for uncontrolled (client-side) sorting. */
  defaultSort?: SortState;
  onRowClick?: (row: T) => void;
  selectedRowKey?: string | null;
  isLoading?: boolean;
  skeletonRows?: number;
  emptyState?: ReactNode;
  /** Accessible table name. */
  'aria-label': string;
  testId?: string;
  stickyHeader?: boolean;
  /** Constrain height so the sticky header has something to stick to. */
  maxHeight?: string;
  rowClassName?: (row: T) => string | undefined;
  className?: string;
}

const HIDE_CLASSES: Record<NonNullable<DataTableColumn<unknown>['hideBelow']>, string> = {
  md: 'hidden md:table-cell',
  lg: 'hidden lg:table-cell',
  xl: 'hidden xl:table-cell',
};

const ALIGN_CLASSES: Record<ColumnAlign, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
};

function compareValues(
  a: string | number | null | undefined,
  b: string | number | null | undefined,
): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

function sortRows<T>(
  rows: ReadonlyArray<T>,
  columns: ReadonlyArray<DataTableColumn<T>>,
  sort: SortState | null,
): ReadonlyArray<T> {
  if (!sort) return rows;
  const column = columns.find((c) => c.id === sort.column);
  if (!column?.sortValue) return rows;
  const accessor = column.sortValue;
  const factor = sort.direction === 'asc' ? 1 : -1;
  return rows
    .map((row, index) => ({ row, index }))
    .sort((x, y) => compareValues(accessor(x.row), accessor(y.row)) * factor || x.index - y.index)
    .map((entry) => entry.row);
}

/**
 * Dense (13px) operational data table.
 *
 * - Sortable headers expose `aria-sort` and toggle asc → desc.
 * - Rows are keyboard-activatable (Enter / Space) when `onRowClick` is given.
 * - Sorting is server-driven when `onSortChange` is supplied, otherwise
 *   client-side via each column's `sortValue`.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  sort,
  onSortChange,
  defaultSort,
  onRowClick,
  selectedRowKey,
  isLoading = false,
  skeletonRows = 8,
  emptyState,
  'aria-label': ariaLabel,
  testId,
  stickyHeader = true,
  maxHeight,
  rowClassName,
  className,
}: DataTableProps<T>) {
  const isControlled = onSortChange !== undefined;
  const [internalSort, setInternalSort] = useState<SortState | null>(defaultSort ?? null);
  const activeSort = isControlled ? (sort ?? null) : internalSort;
  const visibleRows = isControlled ? rows : sortRows(rows, columns, activeSort);
  const interactive = typeof onRowClick === 'function';

  const toggleSort = (columnId: string) => {
    const next: SortState =
      activeSort?.column === columnId
        ? { column: columnId, direction: activeSort.direction === 'asc' ? 'desc' : 'asc' }
        : { column: columnId, direction: 'asc' };
    if (isControlled) onSortChange(next);
    else setInternalSort(next);
  };

  const handleRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!interactive) return;
    if (event.target !== event.currentTarget) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onRowClick(row);
    }
  };

  const showEmpty = !isLoading && visibleRows.length === 0;

  return (
    <div
      className={cn('relative w-full overflow-auto scrollbar-thin', className)}
      style={maxHeight ? { maxHeight } : undefined}
      data-testid={testId}
    >
      <table
        className="w-full min-w-full text-13"
        aria-label={ariaLabel}
        aria-busy={isLoading || undefined}
      >
        <thead
          className={cn(
            'bg-slate-50 text-left text-[11px] font-semibold tracking-wide text-slate-500 uppercase',
            stickyHeader && 'sticky top-0 z-10',
          )}
        >
          <tr>
            {columns.map((column) => {
              const sorted = activeSort?.column === column.id;
              const ariaSort = column.sortable
                ? sorted
                  ? activeSort?.direction === 'asc'
                    ? 'ascending'
                    : 'descending'
                  : 'none'
                : undefined;
              const SortIcon = sorted
                ? activeSort?.direction === 'asc'
                  ? ArrowUp
                  : ArrowDown
                : ArrowUpDown;
              return (
                <th
                  key={column.id}
                  scope="col"
                  aria-sort={ariaSort}
                  style={column.width ? { width: column.width } : undefined}
                  className={cn(
                    'border-b border-slate-200 px-3 py-2 font-semibold whitespace-nowrap',
                    ALIGN_CLASSES[column.align ?? 'left'],
                    column.hideBelow && HIDE_CLASSES[column.hideBelow],
                    column.headerClassName,
                  )}
                >
                  {column.sortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column.id)}
                      className={cn(
                        'group -mx-1 inline-flex items-center gap-1 rounded-sm px-1 py-0.5 tracking-wide uppercase transition-colors hover:text-navy-900',
                        sorted && 'text-navy-900',
                        column.align === 'right' && 'flex-row-reverse',
                      )}
                    >
                      <span>{column.header}</span>
                      <SortIcon
                        aria-hidden="true"
                        className={cn(
                          'size-3 shrink-0 transition-opacity',
                          sorted ? 'opacity-100' : 'opacity-40 group-hover:opacity-80',
                        )}
                      />
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="bg-white">
          {isLoading &&
            Array.from({ length: skeletonRows }, (_, rowIndex) => (
              <tr
                key={`skeleton-${rowIndex}`}
                className="border-b border-slate-100"
                aria-hidden="true"
              >
                {columns.map((column, columnIndex) => (
                  <td
                    key={column.id}
                    className={cn(
                      'px-3 py-2.5',
                      column.hideBelow && HIDE_CLASSES[column.hideBelow],
                    )}
                  >
                    <Skeleton
                      className="h-3.5"
                      style={{
                        width: `${columnIndex === 0 ? 70 : 45 + ((rowIndex + columnIndex) % 4) * 12}%`,
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          {!isLoading &&
            visibleRows.map((row) => {
              const key = rowKey(row);
              const selected = selectedRowKey != null && selectedRowKey === key;
              return (
                <tr
                  key={key}
                  data-row-key={key}
                  tabIndex={interactive ? 0 : undefined}
                  aria-selected={interactive ? selected : undefined}
                  onClick={interactive ? () => onRowClick(row) : undefined}
                  onKeyDown={interactive ? (event) => handleRowKeyDown(event, row) : undefined}
                  className={cn(
                    'border-b border-slate-100 transition-colors last:border-b-0',
                    interactive &&
                      'cursor-pointer hover:bg-slate-50 focus-visible:bg-teal-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600',
                    selected &&
                      'bg-teal-50/70 shadow-[inset_3px_0_0_0_var(--color-teal-600)] hover:bg-teal-50',
                    rowClassName?.(row),
                  )}
                >
                  {columns.map((column) => (
                    <td
                      key={column.id}
                      className={cn(
                        'px-3 py-2 align-middle',
                        ALIGN_CLASSES[column.align ?? 'left'],
                        column.hideBelow && HIDE_CLASSES[column.hideBelow],
                        column.className,
                      )}
                    >
                      {column.cell(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
        </tbody>
      </table>
      {showEmpty && (
        <div className="border-t border-slate-100 bg-white">
          {emptyState ?? (
            <EmptyState
              title="Nothing to show"
              description="No rows match the current filters."
              size="sm"
            />
          )}
        </div>
      )}
    </div>
  );
}
