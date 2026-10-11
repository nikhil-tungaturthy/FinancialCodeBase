import { ChevronDown, UserRound } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/cn';
import { displayNameFromUsername, initials } from '@/lib/format';
import { demoIdentityStore, useDemoIdentity, useUsers } from '@/lib/identity';
import { ROLE_LABELS, humanize } from '@/types/domain';

/**
 * Lets the presenter act as any seeded user. The selection is persisted in
 * `localStorage` (`mf.demoUser`) and sent on every request as `X-Demo-User`.
 * Switching identity invalidates all queries so role-dependent data refetches.
 */
export function IdentitySwitcher() {
  const username = useDemoIdentity();
  const { data: users, isPending, isError } = useUsers();
  const queryClient = useQueryClient();

  const current = users?.find((u) => u.username === username);
  const displayName = current?.display_name ?? displayNameFromUsername(username);
  const roleLabel = current ? (ROLE_LABELS[current.role] ?? humanize(current.role)) : null;

  const onSelect = (next: string) => {
    if (next === username) return;
    demoIdentityStore.setUser(next);
    void queryClient.invalidateQueries();
  };

  if (isPending) {
    return <Skeleton className="h-8 w-44" data-testid="identity-switcher-loading" />;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          data-testid="identity-switcher"
          aria-label={`Demo identity: ${displayName}${roleLabel ? `, ${roleLabel}` : ''}`}
          className={cn(
            'inline-flex h-8 items-center gap-2 rounded-md border border-slate-200 bg-white pr-2 pl-1 text-left text-xs transition-colors',
            'hover:border-slate-300 hover:bg-slate-50 data-[state=open]:border-teal-600 data-[state=open]:ring-2 data-[state=open]:ring-teal-600/20',
          )}
        >
          <span
            aria-hidden="true"
            className="flex size-6 items-center justify-center rounded bg-navy-900 text-[10px] font-semibold text-white"
          >
            {initials(displayName)}
          </span>
          <span className="hidden min-w-0 flex-col leading-tight sm:flex">
            <span className="truncate font-medium text-navy-900">{displayName}</span>
            <span className="truncate text-[10.5px] text-slate-500">
              {roleLabel ?? (isError ? 'Demo identity' : username)}
            </span>
          </span>
          <ChevronDown className="size-3.5 text-slate-400" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="flex items-center gap-1.5">
          <UserRound className="size-3.5" aria-hidden="true" />
          Demo identity
        </DropdownMenuLabel>
        <p className="px-2 pb-2 text-[11px] leading-relaxed text-slate-500">
          Requests are sent with <code className="rounded bg-slate-100 px-1">X-Demo-User</code>.
          Role checks are enforced server-side. This is not production authentication.
        </p>
        <DropdownMenuSeparator />
        {isError || !users ? (
          <p className="px-2 py-3 text-xs text-red-600" role="alert">
            Could not load demo users from the API.
          </p>
        ) : (
          <DropdownMenuRadioGroup value={username} onValueChange={onSelect}>
            {users
              .filter((u) => u.is_active)
              .map((user) => (
                <DropdownMenuRadioItem
                  key={user.username}
                  value={user.username}
                  data-testid={`identity-option-${user.username}`}
                  className="items-start py-2"
                >
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate font-medium text-navy-900">{user.display_name}</span>
                    <span className="truncate text-[11px] text-slate-500">
                      {ROLE_LABELS[user.role] ?? humanize(user.role)} · {user.team}
                    </span>
                  </span>
                </DropdownMenuRadioItem>
              ))}
          </DropdownMenuRadioGroup>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
