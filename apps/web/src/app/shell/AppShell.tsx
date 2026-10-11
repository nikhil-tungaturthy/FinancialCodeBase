import { Outlet } from 'react-router';

import { Sidebar } from '@/app/shell/Sidebar';
import { TopBar } from '@/app/shell/TopBar';

export function AppShell() {
  return (
    <div className="min-h-dvh bg-page">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-navy-900 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex min-h-dvh flex-col pl-rail xl:pl-sidebar">
        <TopBar />
        <main id="main-content" className="flex-1 p-6" tabIndex={-1} data-testid="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
