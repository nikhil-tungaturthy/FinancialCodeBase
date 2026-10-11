import { expect, test } from '@playwright/test';

/**
 * Smoke test for the shell. Runs against the real stack (`make dev`), so it
 * asserts only on structure that does not depend on seeded data volumes.
 */
test.describe('application shell', () => {
  test('renders the sidebar navigation for every primary route', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/Meridian Flow/);
    const sidebar = page.getByTestId('sidebar');
    await expect(sidebar).toBeVisible();

    const expectedLinks: Array<[string, string]> = [
      ['nav-overview', '/'],
      ['nav-payments', '/payments'],
      ['nav-exceptions', '/exceptions'],
      ['nav-settlement', '/settlement'],
      ['nav-approvals', '/approvals'],
      ['nav-audit', '/audit'],
      ['nav-policies', '/policies'],
    ];
    for (const [testId, href] of expectedLinks) {
      const link = sidebar.getByTestId(testId);
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute('href', href);
    }

    await expect(sidebar.getByTestId('nav-overview')).toHaveAttribute('aria-current', 'page');
    await expect(page.getByTestId('topbar-title')).toHaveText('Overview');
    await expect(page.getByTestId('scenario-clock')).toContainText('Scenario time');
    await expect(page.getByTestId('identity-switcher')).toBeVisible();
  });

  test('navigates to the exception workbench and shows the queue', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('nav-exceptions').click();
    await expect(page).toHaveURL(/\/exceptions$/);
    await expect(page.getByTestId('exception-queue')).toBeVisible();
    await expect(page.getByTestId('exception-detail')).toContainText(
      'Select an exception to review',
    );
  });
});
