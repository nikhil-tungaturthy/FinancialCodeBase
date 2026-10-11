import { ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { formatInteger } from '@/lib/format';

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: readonly number[];
  /** Noun for the summary line, e.g. "payments". */
  itemLabel?: string;
  className?: string;
}

function pageWindow(current: number, totalPages: number, span = 2): Array<number | 'gap'> {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  const pages = new Set<number>([1, totalPages]);
  for (let p = current - span; p <= current + span; p += 1) {
    if (p >= 1 && p <= totalPages) pages.add(p);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const result: Array<number | 'gap'> = [];
  for (let i = 0; i < sorted.length; i += 1) {
    const value = sorted[i]!;
    if (i > 0 && value - sorted[i - 1]! > 1) result.push('gap');
    result.push(value);
  }
  return result;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
  itemLabel = 'rows',
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const from = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const to = Math.min(total, safePage * pageSize);

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-600',
        className,
      )}
    >
      <p className="tnum" aria-live="polite">
        {total === 0 ? (
          <>No {itemLabel}</>
        ) : (
          <>
            Showing{' '}
            <span className="font-medium text-slate-800">
              {formatInteger(from)}–{formatInteger(to)}
            </span>{' '}
            of <span className="font-medium text-slate-800">{formatInteger(total)}</span>{' '}
            {itemLabel}
          </>
        )}
      </p>
      <div className="flex items-center gap-3">
        {onPageSizeChange && (
          <label className="flex items-center gap-1.5">
            <span className="text-slate-500">Rows</span>
            <select
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="h-7 rounded-md border border-slate-300 bg-white px-1.5 text-xs text-slate-800"
            >
              {pageSizeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Previous page"
            disabled={safePage <= 1}
            onClick={() => onPageChange(safePage - 1)}
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          {pageWindow(safePage, totalPages).map((entry, index) =>
            entry === 'gap' ? (
              <span key={`gap-${index}`} className="px-1 text-slate-400" aria-hidden="true">
                …
              </span>
            ) : (
              <button
                key={entry}
                type="button"
                aria-current={entry === safePage ? 'page' : undefined}
                aria-label={`Page ${entry}`}
                onClick={() => onPageChange(entry)}
                className={cn(
                  'tnum h-7 min-w-7 rounded-md px-1.5 text-xs transition-colors',
                  entry === safePage
                    ? 'bg-navy-900 font-semibold text-white'
                    : 'text-slate-700 hover:bg-slate-100',
                )}
              >
                {entry}
              </button>
            ),
          )}
          <Button
            variant="ghost"
            size="icon"
            aria-label="Next page"
            disabled={safePage >= totalPages}
            onClick={() => onPageChange(safePage + 1)}
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
