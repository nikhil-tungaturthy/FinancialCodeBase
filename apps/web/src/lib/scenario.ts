import { useQuery } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';

import { apiGet } from '@/lib/api-client';
import { toDate } from '@/lib/dates';
import type { ScenarioMeta } from '@/types/api';

/**
 * Scenario clock (SPEC §0.3).
 *
 * The platform's notion of "now" is fixed by the API (`MF_SCENARIO_NOW`). The
 * frontend never uses the wall clock for ages or countdowns; it reads
 * `/meta/scenario` once and derives everything from `scenario_now`.
 *
 * The instant is held in a small external store so that formatters, sort
 * comparators and primitives such as `CountdownChip` can read it without
 * depending on React Query context.
 */
export const DEFAULT_SCENARIO_NOW_ISO = '2026-03-18T18:40:00Z';

type Listener = () => void;

let cachedScenarioNow: Date = new Date(DEFAULT_SCENARIO_NOW_ISO);
const listeners = new Set<Listener>();

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): Date {
  return cachedScenarioNow;
}

/**
 * Last known scenario instant. Safe to call from non-React code. Falls back to
 * the documented default until the meta endpoint has responded.
 */
export function scenarioNow(): Date {
  return cachedScenarioNow;
}

/** Override the cached instant — called by the scenario query on success and by tests. */
export function setScenarioNow(input: Date | string): void {
  const parsed = toDate(input);
  if (!parsed || parsed.getTime() === cachedScenarioNow.getTime()) return;
  cachedScenarioNow = parsed;
  for (const listener of listeners) listener();
}

export const metaKeys = {
  all: ['meta'] as const,
  scenario: () => [...metaKeys.all, 'scenario'] as const,
};

export async function fetchScenario(signal?: AbortSignal): Promise<ScenarioMeta> {
  const meta = await apiGet<ScenarioMeta>('/meta/scenario', { signal });
  setScenarioNow(meta.scenario_now);
  return meta;
}

export const scenarioQueryOptions = {
  queryKey: metaKeys.scenario(),
  queryFn: ({ signal }: { signal?: AbortSignal }) => fetchScenario(signal),
  staleTime: Infinity,
  gcTime: Infinity,
} as const;

export function useScenario() {
  return useQuery(scenarioQueryOptions);
}

/** The scenario instant as a `Date`; re-renders when the meta endpoint updates it. */
export function useScenarioNow(): Date {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
