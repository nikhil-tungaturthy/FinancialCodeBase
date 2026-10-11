# Contributing to Meridian Flow

Meridian Flow is a demonstration payments-operations platform. All data is synthetic, there
are no external integrations, and nothing here moves real money. The engineering bar is still
that of a production financial system: typed code, explicit money handling, explicit lifecycle
transitions and a complete audit trail. This guide explains how to work in the repository.

## Getting set up

```bash
make setup        # uv sync, npm ci, .env from .env.example (PLAYWRIGHT=1 adds the browser)
make seed         # deterministic synthetic database at data/meridian_flow.db
make dev          # API on http://localhost:8000, web on http://localhost:5173
make test         # backend + frontend tests
```

Details, ports and troubleshooting live in `docs/operations/local-development.md`.
Repository conventions for agents and editors are in `AGENTS.md` and `.cursor/rules/`.

## Branching

- `main` is protected: changes land through pull requests only; no direct pushes, no force
  pushes, linear history.
- Work branches are named by intent and ticket: `feat/MGB-142-resolution-guidance`,
  `fix/MGB-407-sepa-cutoff`, `chore/ci-node-22`, `docs/runbook-settlement-variance`.
- `demo/*` branches are reserved for the presenter segments (see
  `scripts/demo/create_branches.sh`). Do not reuse them for regular work and never rewrite
  their history.
- Rebase onto `main` before requesting review; keep a branch to one logical change.

## Commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative summary, lower case, no trailing period>

<body: what and why, wrapped at 100 columns>

Refs: MGB-318
```

- Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`.
- Scopes mirror the repository: `api`, `batch`, `web`, `legacy`, `seed`, `policies`, `docs`,
  `ci`, `scripts`.
- Reference the MGB ticket in the footer (`Refs:` or `Closes:`). Tickets live in
  `docs/product/tickets/`.
- A commit that changes money, rounding, lifecycle transitions, audit behaviour or cutoff
  timing says so in the body, with the rule it implements.

## Pull requests

Fill in the template at `.github/pull_request_template.md` in full. A PR is ready for review
when:

1. `make lint`, `make typecheck` and `make test` pass locally.
2. The financial-impact checklist in the template is answered (Decimal, rounding, transitions,
   audit events, timezone).
3. New or changed API shapes are reflected in `shared/contracts/openapi.json`
   (`make contracts`) and the generated TypeScript types.
4. User-visible changes include screenshots or a short recording.
5. The seed still verifies (`make seed-verify`) if seed data or domain rules changed.

Keep PRs small. A PR that touches more than one area (for example API and web) is fine when
the change is one feature, but split unrelated refactors out.

## Review policy

A pull request merges only when all of the following hold:

- **CODEOWNERS approval.** At least one approving review from an owner of every path the PR
  touches (`.github/CODEOWNERS`). Authors cannot approve their own PRs.
- **CI green.** All jobs in `.github/workflows/ci.yml` (backend, frontend, e2e, legacy) pass on
  the final commit.
- **No Decimal/float regressions.** Monetary values stay `decimal.Decimal` in Python business
  logic and strings on the wire and in the frontend. Reviewers reject `float` arithmetic on
  amounts, implicit rounding, or `Number(...)` conversions of amounts in `apps/web`.
- **No new audit gaps.** Every state-changing operation records an `AuditEvent` through
  `app.audit.recorder.record_audit_event`. A new endpoint, service method or batch step that
  mutates state without an audit event is a blocking finding.
- **Explicit transitions only.** Payment, exception, approval and batch status changes go
  through the lifecycle module; direct status assignment is rejected.
- **Scenario clock.** Business code uses `app.core.clock.now()`; `datetime.now()` in business
  logic is rejected (the `DTZ` ruff rules enforce timezone awareness).
- **Legacy parity.** Changes to fee or routing behaviour keep
  `legacy/reference-tests` green; golden fixtures change only with an ADR update.

Reviewers write findings as questions or specific requests, cite the rule or ticket, and
distinguish blocking items from suggestions.

## Running tests

| Command              | What runs                                                                 |
| -------------------- | ------------------------------------------------------------------------- |
| `make test-api`      | pytest for `services/api`, `services/batch` and `legacy/reference-tests`  |
| `make test-web`      | vitest (single run) for `apps/web`                                        |
| `make test-e2e`      | Playwright against a running API + web (`make dev` then `make ready`)     |
| `make test`          | `test-api` + `test-web`                                                   |
| `make lint`          | ruff check, ruff format --check, eslint                                   |
| `make typecheck`     | mypy (strict) for `app/` and `batch/`, `tsc --noEmit` for the web app     |
| `make seed-verify`   | re-derives the seed invariants and fails on any violation                 |

The COBOL golden test compiles and runs `FEECALC01` when `cobc` (GnuCOBOL) is on `PATH`;
otherwise it validates the Python reference implementation against the fixtures and reports a
skip for the COBOL execution.

## Code style

- Python 3.12, `ruff` for linting and formatting (100 columns), `mypy --strict` clean for
  `services/api/app` and `services/batch/batch`. Public functions are typed; money is
  `Decimal`; datetimes are timezone-aware.
- TypeScript strict, ESLint (`typescript-eslint`, `react-hooks`, `jsx-a11y`), Prettier.
  Amounts are strings formatted with `Intl.NumberFormat` at render time.
- Tests live next to the layer they cover (`tests/unit`, `tests/domain`, `tests/integration`,
  `tests/api`); deterministic data only, no sleeps, no network.
- No placeholder text, no commented-out code, no TODOs that encode ticket answers.

## Documentation and tickets

Docs are American English, concise and factual. Architecture decisions go in
`docs/architecture/adr/`; operational procedures in `docs/operations/`; product work items
in `docs/product/tickets/MGB-xxx.md` with the standard sections (Summary, Business problem,
Requested behavior, Acceptance criteria, Out of scope, Relevant areas, Notes).

## What never goes in

- Real customer, counterparty or bank data of any kind, including "anonymised" extracts.
- Credentials, tokens or keys (there are none in this project; keep it that way).
- Calls to external services from application or batch code.
- Non-deterministic seed data (`uuid4()`, wall-clock timestamps) or float money.
