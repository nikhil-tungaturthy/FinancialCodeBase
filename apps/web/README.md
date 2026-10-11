# Meridian Flow — web console

React 19 + Vite 7 + TypeScript front end for the Meridian Flow payments operations platform. It talks to the FastAPI service at `/api/v1` (proxied to `http://localhost:8000` in development).

## Scripts

Run from the repository root with `-w apps/web`, or from this directory.

| Script                   | Purpose                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| `npm run dev`            | Vite dev server on `http://localhost:5173` (strict port; `/api` proxied to the API)                     |
| `npm run build`          | Type-check (`tsc -b`) and produce the production bundle in `dist/`                                      |
| `npm run preview`        | Serve the production bundle locally                                                                     |
| `npm run test`           | Vitest (jsdom + Testing Library + MSW); add `-- --run` for a single pass                                |
| `npm run test:e2e`       | Playwright smoke tests against an already-running stack (`make dev`)                                    |
| `npm run lint`           | ESLint flat config (TypeScript, React hooks, React Refresh, jsx-a11y)                                   |
| `npm run typecheck`      | `tsc --noEmit` for the app project                                                                      |
| `npm run format`         | Prettier                                                                                                |
| `npm run generate:types` | Regenerate `src/types/api.generated.ts` from `shared/contracts/openapi.json` (run via `make contracts`) |

## Structure

```
src/
  app/            router, providers, shell (Sidebar, TopBar, ScenarioClock, IdentitySwitcher), error pages
  components/ui/  design-system primitives (Button, DataTable, StatusPill, Money, CountdownChip, Drawer, Toast …)
  features/<area>/{api.ts,hooks.ts,components/,pages/}   overview · payments · exceptions · settlement · approvals · audit · policies
  lib/            api-client, query-client, identity store, scenario clock, money/date/format helpers
  styles/         globals.css — Tailwind v4 `@theme` tokens (navy / teal / amber / red / green, Inter, radii)
  test/           Vitest setup, provider-wrapped `renderWithProviders`, MSW handlers
  types/          domain.ts (enums, labels, tones), api.ts (hand-written contract), api.generated.ts (generated)
e2e/              Playwright specs
```

## Conventions

- **Money is a string.** The API serialises amounts as decimal strings; the UI never does arithmetic on them. Render with `<Money amount currency />`, which applies the currency's minor units (JPY 0dp) and tabular figures.
- **Time is UTC and fixed.** All timestamps render in UTC (`18:40 UTC · 18 Mar 2026`). Ages and countdowns use the scenario clock from `/meta/scenario` (`useScenarioNow()` / `scenarioNow()`), never `Date.now()`.
- **Identity is a header.** `useDemoIdentity()` exposes the selected demo user; the API client sends it as `X-Demo-User`. Role checks happen server-side.
- **Data fetching.** One `api.ts` (typed fetchers) and one `hooks.ts` (TanStack Query hooks + key factories) per feature. List state (page, sort, filters) lives in the URL via `lib/url-state.ts`.
- **Errors.** Non-2xx responses throw `ApiError` with the parsed problem+json body and correlation id; render with `<ErrorState error onRetry />`.
- **Accessibility.** Tables expose `aria-sort`; rows are keyboard-activatable (Enter/Space); every icon-only control has an accessible name; Radix primitives supply focus management for dialogs, menus, selects and tabs.
- **Styling.** Tailwind utilities with tokens from `globals.css`; compose class names with `cn()`. Dense tables use `text-13`; numbers use `tnum`.

## Test ids

Key regions carry `data-testid` attributes for Playwright and component tests:

`sidebar`, `nav-<route>`, `topbar`, `topbar-title`, `scenario-clock`, `identity-switcher`, `identity-option-<username>`, `overview-kpis`, `payments-table`, `payment-detail`, `exception-queue`, `exception-detail`, `batch-table`, `batch-detail`, `batch-entries`, `batch-unmatched`, `approvals-table`, `approval-detail`, `audit-table`, `policy-tabs`.
