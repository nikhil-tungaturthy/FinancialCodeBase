import { ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { cn } from '@/lib/cn';

export interface Breadcrumb {
  label: ReactNode;
  to?: string;
}

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  /** Small label above the title, e.g. the entity type or ref. */
  eyebrow?: ReactNode;
  breadcrumbs?: ReadonlyArray<Breadcrumb>;
  actions?: ReactNode;
  /** Inline status content rendered next to the title (pills, chips). */
  meta?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  breadcrumbs,
  actions,
  meta,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('mb-5 flex flex-col gap-3', className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="text-xs text-slate-500">
          <ol className="flex flex-wrap items-center gap-1">
            {breadcrumbs.map((crumb, index) => {
              const last = index === breadcrumbs.length - 1;
              return (
                <li key={index} className="flex items-center gap-1">
                  {crumb.to && !last ? (
                    <Link
                      to={crumb.to}
                      className="transition-colors hover:text-navy-900 hover:underline"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span
                      aria-current={last ? 'page' : undefined}
                      className={cn(last && 'font-medium text-slate-700')}
                    >
                      {crumb.label}
                    </span>
                  )}
                  {!last && <ChevronRight className="size-3 text-slate-400" aria-hidden="true" />}
                </li>
              );
            })}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-[11px] font-semibold tracking-wider text-teal-700 uppercase">
              {eyebrow}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <h1 className="text-xl leading-7 font-semibold tracking-tight text-navy-900">
              {title}
            </h1>
            {meta && <div className="flex flex-wrap items-center gap-1.5">{meta}</div>}
          </div>
          {description && <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
