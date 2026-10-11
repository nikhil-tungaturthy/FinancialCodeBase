import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { IdentitySwitcher } from '@/app/shell/IdentitySwitcher';
import { apiGet } from '@/lib/api-client';
import { DEFAULT_DEMO_USER, DEMO_USER_STORAGE_KEY, demoIdentityStore } from '@/lib/identity';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/render';

describe('IdentitySwitcher', () => {
  beforeEach(() => {
    demoIdentityStore.setUser(DEFAULT_DEMO_USER);
  });

  it('shows the current demo user with their role once users load', async () => {
    renderWithProviders(<IdentitySwitcher />);
    const trigger = await screen.findByTestId('identity-switcher');
    expect(trigger).toHaveAccessibleName('Demo identity: Priya Raman, Analyst');
    expect(trigger).toHaveTextContent('Priya Raman');
    expect(trigger).toHaveTextContent('Analyst');
  });

  it('persists the selected identity to localStorage and updates the header sent to the API', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IdentitySwitcher />);

    await user.click(await screen.findByTestId('identity-switcher'));
    const option = await screen.findByTestId('identity-option-marcus.okafor');
    expect(option).toHaveAttribute('role', 'menuitemradio');
    await user.click(option);

    await waitFor(() =>
      expect(window.localStorage.getItem(DEMO_USER_STORAGE_KEY)).toBe('marcus.okafor'),
    );
    expect(demoIdentityStore.getSnapshot()).toBe('marcus.okafor');
    expect(await screen.findByText('Marcus Okafor')).toBeInTheDocument();

    let seenHeader: string | null = null;
    server.use(
      http.get('/api/v1/users/me', ({ request }) => {
        seenHeader = request.headers.get('X-Demo-User');
        return HttpResponse.json({
          username: 'marcus.okafor',
          display_name: 'Marcus Okafor',
          email: 'm@x',
          role: 'SUPERVISOR',
          team: 'Payments Operations',
          is_active: true,
        });
      }),
    );
    await apiGet('/users/me');
    expect(seenHeader).toBe('marcus.okafor');
  });

  it('lists every active seeded user as a radio option', async () => {
    const user = userEvent.setup();
    renderWithProviders(<IdentitySwitcher />);
    await user.click(await screen.findByTestId('identity-switcher'));
    const options = await screen.findAllByRole('menuitemradio');
    expect(options).toHaveLength(6);
    expect(options.find((o) => o.getAttribute('aria-checked') === 'true')).toHaveTextContent(
      'Priya Raman',
    );
  });

  it('surfaces an error inside the menu when the users endpoint fails', async () => {
    const user = userEvent.setup();
    server.use(
      http.get('/api/v1/users', () =>
        HttpResponse.json({ title: 'Service unavailable', status: 503 }, { status: 503 }),
      ),
    );
    renderWithProviders(<IdentitySwitcher />);
    await user.click(await screen.findByTestId('identity-switcher'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load demo users');
  });
});
