import { NavLink } from 'react-router';

import { APP_NAME, APP_TAGLINE, ENVIRONMENT_TAG, NAV_ITEMS } from '@/app/navigation';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="7" fill="#1B3357" />
      <path
        d="M7 23V9.5l9 8 9-8V23"
        fill="none"
        stroke="#14B8A6"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Primary navigation. Full width (232px) from 1280px up; collapses to a 64px
 * icon rail below that, with tooltips supplying the hidden labels.
 */
export function Sidebar() {
  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex w-rail flex-col bg-navy-900 text-slate-200 xl:w-sidebar"
      aria-label="Primary"
      data-testid="sidebar"
    >
      <div className="flex h-topbar items-center gap-3 border-b border-white/10 px-3 xl:px-4">
        <BrandMark />
        <div className="hidden min-w-0 xl:block">
          <p className="truncate text-sm leading-tight font-semibold text-white">{APP_NAME}</p>
          <p className="truncate text-[10.5px] leading-tight text-slate-400">{APP_TAGLINE}</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 scrollbar-thin" aria-label="Main navigation">
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const link = (
              <NavLink
                to={item.to}
                end={item.end}
                data-testid={item.testId}
                className={({ isActive }) =>
                  cn(
                    'group relative flex h-9 items-center gap-3 rounded-md px-2.5 text-[13px] font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500',
                    isActive
                      ? 'bg-white/10 text-white shadow-[inset_3px_0_0_0_var(--color-teal-500)]'
                      : 'text-slate-300 hover:bg-white/5 hover:text-white',
                    'justify-center xl:justify-start',
                  )
                }
              >
                <Icon className="size-[18px] shrink-0" aria-hidden="true" />
                <span className="hidden truncate xl:inline">{item.label}</span>
                <span className="sr-only xl:hidden">{item.label}</span>
              </NavLink>
            );
            return (
              <li key={item.to}>
                <div className="xl:hidden">
                  <Tooltip content={item.label} side="right">
                    {link}
                  </Tooltip>
                </div>
                <div className="hidden xl:block">{link}</div>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-white/10 p-3">
        <div
          className="flex items-center justify-center rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-center text-[10px] font-semibold tracking-wider text-amber-100"
          title="All data in this environment is synthetic. No real customers, banks or payments."
        >
          <span className="hidden xl:inline">{ENVIRONMENT_TAG}</span>
          <span className="xl:hidden">DEMO</span>
        </div>
      </div>
    </aside>
  );
}
