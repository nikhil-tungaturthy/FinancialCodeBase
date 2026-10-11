import { useQuery } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';

import { apiGet } from '@/lib/api-client';
import type { User } from '@/types/api';

/**
 * Demo identity store.
 *
 * Meridian Flow has no production authentication: the API trusts an
 * `X-Demo-User` header naming one of the seeded users (SPEC §4). The current
 * selection is a tiny external store so that the fetch wrapper (plain module
 * code) and React components (`useDemoIdentity`) share the same value.
 */
export const DEMO_USER_STORAGE_KEY = 'mf.demoUser';
export const DEFAULT_DEMO_USER = 'priya.raman';

type Listener = () => void;

function readPersisted(): string {
  try {
    const stored = globalThis.localStorage?.getItem(DEMO_USER_STORAGE_KEY);
    return stored && stored.trim() ? stored : DEFAULT_DEMO_USER;
  } catch {
    return DEFAULT_DEMO_USER;
  }
}

function persist(username: string): void {
  try {
    globalThis.localStorage?.setItem(DEMO_USER_STORAGE_KEY, username);
  } catch {
    // Storage may be unavailable (private mode, blocked). The in-memory value still applies.
  }
}

let current: string = readPersisted();
const listeners = new Set<Listener>();

export const demoIdentityStore = {
  getSnapshot(): string {
    return current;
  },
  getServerSnapshot(): string {
    return DEFAULT_DEMO_USER;
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
  setUser(username: string): void {
    const next = username.trim() || DEFAULT_DEMO_USER;
    if (next === current) return;
    current = next;
    persist(next);
    for (const listener of listeners) listener();
  },
  /** Re-read from storage — used when another tab changes the selection. */
  refreshFromStorage(): void {
    const next = readPersisted();
    if (next === current) return;
    current = next;
    for (const listener of listeners) listener();
  },
};

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === DEMO_USER_STORAGE_KEY) demoIdentityStore.refreshFromStorage();
  });
}

/** The username currently sent as `X-Demo-User`. */
export function useDemoIdentity(): string {
  return useSyncExternalStore(
    demoIdentityStore.subscribe,
    demoIdentityStore.getSnapshot,
    demoIdentityStore.getServerSnapshot,
  );
}

export const userKeys = {
  all: ['users'] as const,
  list: () => [...userKeys.all, 'list'] as const,
  me: (username: string) => [...userKeys.all, 'me', username] as const,
};

export function fetchUsers(signal?: AbortSignal): Promise<User[]> {
  return apiGet<User[] | { items: User[] }>('/users', { signal }).then((payload) =>
    Array.isArray(payload) ? payload : payload.items,
  );
}

export function fetchCurrentUser(signal?: AbortSignal): Promise<User> {
  return apiGet<User>('/users/me', { signal });
}

export function useUsers() {
  return useQuery({
    queryKey: userKeys.list(),
    queryFn: ({ signal }) => fetchUsers(signal),
    staleTime: Infinity,
  });
}

export function useCurrentUser() {
  const username = useDemoIdentity();
  return useQuery({
    queryKey: userKeys.me(username),
    queryFn: ({ signal }) => fetchCurrentUser(signal),
    staleTime: Infinity,
  });
}
