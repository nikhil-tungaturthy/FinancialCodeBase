import { useEffect } from 'react';

import { APP_NAME, APP_TAGLINE } from '@/app/navigation';
import { IdentitySwitcher } from '@/app/shell/IdentitySwitcher';
import { ScenarioClock } from '@/app/shell/ScenarioClock';
import { useRouteTitle } from '@/app/shell/use-route-title';

export function TopBar() {
  const title = useRouteTitle();

  useEffect(() => {
    document.title = title === APP_NAME ? `${APP_NAME} · ${APP_TAGLINE}` : `${title} · ${APP_NAME}`;
  }, [title]);

  return (
    <header
      className="sticky top-0 z-20 flex h-topbar items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-6 backdrop-blur-sm"
      data-testid="topbar"
    >
      <h2 className="truncate text-[15px] font-semibold text-navy-900" data-testid="topbar-title">
        {title}
      </h2>
      <div className="flex items-center gap-3">
        <ScenarioClock />
        <IdentitySwitcher />
      </div>
    </header>
  );
}
