import { useMatches, useParams } from 'react-router';

import { APP_NAME, type RouteHandle } from '@/app/navigation';

function isRouteHandle(value: unknown): value is RouteHandle {
  return typeof value === 'object' && value !== null && 'title' in value;
}

/** Resolve the deepest route handle title for the current location. */
export function useRouteTitle(): string {
  const matches = useMatches();
  const params = useParams();
  for (let index = matches.length - 1; index >= 0; index -= 1) {
    const handle = matches[index]?.handle;
    if (isRouteHandle(handle)) {
      return typeof handle.title === 'function' ? handle.title(params) : handle.title;
    }
  }
  return APP_NAME;
}
