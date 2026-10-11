import { http, HttpResponse } from 'msw';

import type { ScenarioMeta, User } from '@/types/api';

export const SCENARIO_FIXTURE: ScenarioMeta = {
  scenario_now: '2026-03-18T18:40:00+00:00',
  scenario_date: '2026-03-18',
  business_day_label: 'Wednesday 18 March 2026',
  seed_version: '2026.03.1',
  display_timezone: 'UTC',
  fx_reference_rates: {
    USD: '1',
    EUR: '1.0850',
    GBP: '1.2700',
    CHF: '1.1200',
    JPY: '0.0067',
    SGD: '0.7450',
  },
  environment: 'demo',
};

export const USERS_FIXTURE: User[] = [
  {
    username: 'priya.raman',
    display_name: 'Priya Raman',
    email: 'priya.raman@meridianglobal.example',
    role: 'ANALYST',
    team: 'Payments Operations',
    is_active: true,
  },
  {
    username: 'marcus.okafor',
    display_name: 'Marcus Okafor',
    email: 'marcus.okafor@meridianglobal.example',
    role: 'SUPERVISOR',
    team: 'Payments Operations',
    is_active: true,
  },
  {
    username: 'elena.vasquez',
    display_name: 'Elena Vasquez',
    email: 'elena.vasquez@meridianglobal.example',
    role: 'PAYMENTS_MANAGER',
    team: 'Payments Operations',
    is_active: true,
  },
  {
    username: 'tomasz.nowak',
    display_name: 'Tomasz Nowak',
    email: 'tomasz.nowak@meridianglobal.example',
    role: 'RISK_OFFICER',
    team: 'Financial Crime Risk',
    is_active: true,
  },
  {
    username: 'aisha.bello',
    display_name: 'Aisha Bello',
    email: 'aisha.bello@meridianglobal.example',
    role: 'ANALYST',
    team: 'Settlement & Reconciliation',
    is_active: true,
  },
  {
    username: 'devon.hart',
    display_name: 'Devon Hart',
    email: 'devon.hart@meridianglobal.example',
    role: 'ENGINEER',
    team: 'Payments Platform Engineering',
    is_active: true,
  },
];

export const handlers = [
  http.get('/api/v1/meta/scenario', () => HttpResponse.json(SCENARIO_FIXTURE)),
  http.get('/api/v1/users', () => HttpResponse.json(USERS_FIXTURE)),
  http.get('/api/v1/users/me', ({ request }) => {
    const username = request.headers.get('X-Demo-User') ?? 'priya.raman';
    const user = USERS_FIXTURE.find((u) => u.username === username);
    if (!user) {
      return HttpResponse.json(
        {
          type: 'about:blank',
          title: 'Unknown demo identity',
          status: 401,
          detail: `No user '${username}'`,
        },
        { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
      );
    }
    return HttpResponse.json(user);
  }),
];
