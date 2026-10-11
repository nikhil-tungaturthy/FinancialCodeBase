/** Helpers for keeping list state (page, sort, filters) in the URL search params. */

export function readInt(params: URLSearchParams, key: string, fallback: number): number {
  const raw = params.get(key);
  if (raw === null) return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function readString(params: URLSearchParams, key: string): string | undefined {
  const raw = params.get(key);
  return raw && raw.trim() ? raw : undefined;
}

export function readList(params: URLSearchParams, key: string): string[] {
  return params.getAll(key).filter((value) => value.trim() !== '');
}

export function readEnum<T extends string>(
  params: URLSearchParams,
  key: string,
  allowed: readonly T[],
): T | undefined {
  const raw = params.get(key);
  return raw && (allowed as readonly string[]).includes(raw) ? (raw as T) : undefined;
}

export type ParamPatch = Record<string, string | number | null | undefined | ReadonlyArray<string>>;

/**
 * Produce the next search params from a patch. `null`/`undefined`/`''` remove a
 * key; arrays are written as repeated keys. Any change other than `page` resets
 * the page to 1 unless the patch sets it explicitly.
 */
export function patchParams(previous: URLSearchParams, patch: ParamPatch): URLSearchParams {
  const next = new URLSearchParams(previous);
  let touchedNonPage = false;
  for (const [key, value] of Object.entries(patch)) {
    if (key !== 'page') touchedNonPage = true;
    next.delete(key);
    if (value === null || value === undefined || value === '') continue;
    if (Array.isArray(value)) {
      for (const item of value) if (item !== '') next.append(key, item);
    } else {
      next.set(key, String(value));
    }
  }
  if (touchedNonPage && !('page' in patch)) next.delete('page');
  return next;
}
