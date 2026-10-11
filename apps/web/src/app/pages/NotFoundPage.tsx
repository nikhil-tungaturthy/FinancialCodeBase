import { Compass } from 'lucide-react';
import { Link, useLocation } from 'react-router';

import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';

export default function NotFoundPage() {
  const location = useLocation();
  return (
    <div className="mx-auto max-w-lg rounded-lg border border-slate-200 bg-white shadow-card">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description={
          <>
            There is nothing at{' '}
            <code className="rounded bg-slate-100 px-1">{location.pathname}</code>. The link may be
            out of date or the reference may have been mistyped.
          </>
        }
        action={
          <Button asChild>
            <Link to="/">Back to overview</Link>
          </Button>
        }
      />
    </div>
  );
}
