import { demoIdentityStore } from '@/lib/identity';
import type { ProblemDetails } from '@/types/api';

export const API_BASE_URL = '/api/v1';
export const CORRELATION_HEADER = 'X-Correlation-ID';
export const DEMO_USER_HEADER = 'X-Demo-User';

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | ReadonlyArray<string | number>>;

export interface RequestOptions {
  /** Query string parameters. Arrays are always serialised as repeated keys (`status=A&status=B`). */
  query?: QueryParams;
  /** Correlation id to forward; the API honours an inbound header and echoes it back. */
  correlationId?: string;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

/** Thrown for any non-2xx response. Carries the parsed problem+json body when available. */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails | null;
  readonly correlationId: string | null;
  readonly url: string;

  constructor(args: {
    status: number;
    url: string;
    problem: ProblemDetails | null;
    correlationId: string | null;
    fallbackMessage?: string;
  }) {
    const message =
      args.problem?.detail ??
      args.problem?.title ??
      args.fallbackMessage ??
      `Request failed with status ${args.status}`;
    super(message);
    this.name = 'ApiError';
    this.status = args.status;
    this.url = args.url;
    this.problem = args.problem;
    this.correlationId = args.correlationId;
  }

  get title(): string {
    return this.problem?.title ?? defaultTitleFor(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }

  get isValidation(): boolean {
    return this.status === 422;
  }
}

/** Raised when the network request itself fails (offline, proxy down, aborted by timeout). */
export class NetworkError extends Error {
  readonly url: string;
  constructor(url: string, cause: unknown) {
    super('Unable to reach the Meridian Flow API');
    this.name = 'NetworkError';
    this.url = url;
    this.cause = cause;
  }
}

function defaultTitleFor(status: number): string {
  switch (status) {
    case 400:
      return 'Bad request';
    case 401:
      return 'Unknown demo identity';
    case 403:
      return 'Not permitted for this role';
    case 404:
      return 'Not found';
    case 409:
      return 'Conflict';
    case 422:
      return 'Validation failed';
    case 503:
      return 'Service unavailable';
    default:
      return status >= 500 ? 'Server error' : 'Request failed';
  }
}

export function buildQueryString(query: QueryParams | undefined): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, String(item));
    } else {
      params.append(key, String(value));
    }
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : '';
}

export function buildUrl(path: string, query?: QueryParams): string {
  const normalised = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalised}${buildQueryString(query)}`;
}

async function parseProblem(response: Response): Promise<ProblemDetails | null> {
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('json')) return null;
  try {
    const body = (await response.json()) as Partial<ProblemDetails> & Record<string, unknown>;
    if (body && typeof body === 'object' && ('title' in body || 'detail' in body)) {
      return {
        type: typeof body.type === 'string' ? body.type : 'about:blank',
        title: typeof body.title === 'string' ? body.title : defaultTitleFor(response.status),
        status: typeof body.status === 'number' ? body.status : response.status,
        detail: typeof body.detail === 'string' ? body.detail : undefined,
        instance: typeof body.instance === 'string' ? body.instance : undefined,
        correlation_id: typeof body.correlation_id === 'string' ? body.correlation_id : undefined,
        errors: Array.isArray(body.errors) ? (body.errors as ProblemDetails['errors']) : undefined,
      };
    }
    return null;
  } catch {
    return null;
  }
}

async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, options.query);
  const headers: Record<string, string> = {
    Accept: 'application/json, application/problem+json',
    [DEMO_USER_HEADER]: demoIdentityStore.getSnapshot(),
    ...options.headers,
  };
  if (options.correlationId) headers[CORRELATION_HEADER] = options.correlationId;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: options.signal,
      credentials: 'same-origin',
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new NetworkError(url, error);
  }

  const correlationId = response.headers.get(CORRELATION_HEADER);

  if (!response.ok) {
    const problem = await parseProblem(response);
    throw new ApiError({
      status: response.status,
      url,
      problem,
      correlationId: problem?.correlation_id ?? correlationId,
    });
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>('GET', path, undefined, options);
}

export function apiPost<T, B = unknown>(
  path: string,
  body?: B,
  options?: RequestOptions,
): Promise<T> {
  return request<T>('POST', path, body, options);
}

export function apiPut<T, B = unknown>(
  path: string,
  body: B,
  options?: RequestOptions,
): Promise<T> {
  return request<T>('PUT', path, body, options);
}

export function apiDelete<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>('DELETE', path, undefined, options);
}

/** Human-readable message for any error surfaced by the API client or React Query. */
export function describeError(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiError) {
    return { title: error.title, detail: error.message };
  }
  if (error instanceof NetworkError) {
    return {
      title: 'API unreachable',
      detail:
        'Could not reach the Meridian Flow API. Check that the service is running on port 8000.',
    };
  }
  if (error instanceof Error) {
    return { title: 'Something went wrong', detail: error.message };
  }
  return { title: 'Something went wrong', detail: 'An unexpected error occurred.' };
}
