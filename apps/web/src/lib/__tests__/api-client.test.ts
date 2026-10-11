import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ApiError, apiGet, apiPost, buildQueryString, describeError } from '@/lib/api-client';
import { server } from '@/test/msw/server';

describe('api-client', () => {
  it('serialises arrays as repeated keys and drops empty values', () => {
    expect(
      buildQueryString({ status: ['OPEN', 'IN_REVIEW'], page: 2, search: '', rail: undefined }),
    ).toBe('?status=OPEN&status=IN_REVIEW&page=2');
    expect(buildQueryString(undefined)).toBe('');
  });

  it('sends the demo identity header and forwards an explicit correlation id', async () => {
    let headers: Headers | null = null;
    server.use(
      http.get('/api/v1/ping', ({ request }) => {
        headers = request.headers;
        return HttpResponse.json({ ok: true }, { headers: { 'X-Correlation-ID': 'corr-echo' } });
      }),
    );
    await expect(apiGet('/ping', { correlationId: 'corr-123' })).resolves.toEqual({ ok: true });
    expect(headers!.get('X-Demo-User')).toBe('priya.raman');
    expect(headers!.get('X-Correlation-ID')).toBe('corr-123');
  });

  it('throws an ApiError carrying problem+json details and the correlation id', async () => {
    server.use(
      http.post('/api/v1/exceptions/MGB-EXC-0231/actions', () =>
        HttpResponse.json(
          {
            type: 'https://meridian.example/problems/invalid-transition',
            title: 'Invalid transition',
            status: 409,
            detail: 'Exception MGB-EXC-0231 cannot move from RESOLVED to IN_REVIEW',
            correlation_id: 'corr-pay-1042',
          },
          { status: 409, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    const promise = apiPost('/exceptions/MGB-EXC-0231/actions', {
      action: 'ESCALATE',
      justification: 'x',
    });
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    const error = (await promise.catch((e: unknown) => e)) as ApiError;
    expect(error.status).toBe(409);
    expect(error.isConflict).toBe(true);
    expect(error.title).toBe('Invalid transition');
    expect(error.message).toContain('cannot move from RESOLVED');
    expect(error.correlationId).toBe('corr-pay-1042');
    expect(describeError(error)).toEqual({ title: 'Invalid transition', detail: error.message });
  });

  it('falls back to a status-based title when the body is not problem+json', async () => {
    server.use(http.get('/api/v1/payments/NOPE', () => new HttpResponse('gone', { status: 404 })));
    const error = (await apiGet('/payments/NOPE').catch((e: unknown) => e)) as ApiError;
    expect(error.isNotFound).toBe(true);
    expect(error.title).toBe('Not found');
    expect(error.problem).toBeNull();
  });
});
