import { AlertOctagon, Home, RotateCw } from 'lucide-react';
import { isRouteErrorResponse, Link, useNavigate, useRouteError } from 'react-router';

import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api-client';

/** Rendered by the data router when a route element throws during render or loading. */
export default function RouteErrorPage() {
  const error = useRouteError();
  const navigate = useNavigate();

  let title = 'Something went wrong';
  let detail = 'An unexpected error occurred while rendering this page.';
  let status: number | null = null;

  if (isRouteErrorResponse(error)) {
    status = error.status;
    title = error.status === 404 ? 'Page not found' : error.statusText || title;
    detail = typeof error.data === 'string' && error.data ? error.data : detail;
  } else if (error instanceof Error) {
    const described = describeError(error);
    title = described.title;
    detail = described.detail;
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-page p-6" role="alert">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 text-center shadow-card">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-red-100 text-red-600">
          <AlertOctagon className="size-5" aria-hidden="true" />
        </span>
        {status && (
          <p className="mt-4 text-xs font-semibold tracking-wider text-slate-400 uppercase">
            Error {status}
          </p>
        )}
        <h1 className="mt-1 text-lg font-semibold text-navy-900">{title}</h1>
        <p className="mt-2 text-sm text-slate-500">{detail}</p>
        {error instanceof Error && import.meta.env.DEV && (
          <pre className="mt-4 max-h-40 overflow-auto rounded-md bg-slate-50 p-3 text-left text-[11px] text-slate-600">
            {error.stack ?? error.message}
          </pre>
        )}
        <div className="mt-6 flex justify-center gap-2">
          <Button variant="outline" onClick={() => navigate(0)}>
            <RotateCw aria-hidden="true" />
            Reload
          </Button>
          <Button asChild>
            <Link to="/">
              <Home aria-hidden="true" />
              Back to overview
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
