# ADR 0001: Monorepo and technology stack

* Status: Accepted
* Date: 2026-03-02
* Deciders: Payments Platform Engineering

## Context

Meridian Flow replaces a payments operations estate made up of a mainframe
batch (COBOL), a desktop review client (VB6) and spreadsheets. The replacement
has three deliverables that must evolve together: an HTTP API with the domain
model, a set of batch jobs that share that domain model, and an operations web
application. The retired components' behavior must be preserved and tested
alongside the new code (see ADR 0003), and the whole system must run on a
laptop from a single checkout for demonstrations and incident drills.

## Decision

One repository, two package managers, one command surface.

**Layout**

```
services/api     Python package `app`   - FastAPI API, domain model, seed
services/batch   Python package `batch` - settlement and reconciliation jobs (depends on `app`)
apps/web         Vite + React operations UI
legacy/          COBOL and VB6 sources, Python golden-master tests, fixtures
shared/          OpenAPI contract and shared fixtures (incident evidence)
docs/            architecture, operations, product, engineering, integrations
scripts/         setup, dev, demo reset, incident emit, contract export
```

**Python** 3.12 managed by `uv` as a workspace rooted at the repository
(`pyproject.toml` lists `services/api` and `services/batch` as members, both
installed editable, so `uv run` works from the root). Pinned: FastAPI 0.143,
Pydantic 2.14, pydantic-settings 2.15, SQLAlchemy 2.0 (`<2.1`, Mapped-style
models), structlog 26, typer 0.27, rich 15, tzdata. Dev: pytest 9, pytest-cov,
httpx, ruff 0.17, mypy 2.4 (strict), freezegun. Quality bar: ruff-clean and
mypy-strict for `app/` and `batch/`.

**Node** 22 LTS in CI (24 locally is fine) with npm workspaces and a single root
lock file. React 19, React Router 7 (data router), TanStack Query 5, Recharts
3, Vite 7, TypeScript 5.9 strict, Tailwind 4, Radix primitives, bundled Inter
font (no network fonts). Tests: Vitest, Testing Library, Playwright. Lint:
ESLint 9 flat config with typescript-eslint, react-hooks, jsx-a11y; Prettier.

**Contract.** The API is the source of truth: `scripts/export_openapi.py`
writes `shared/contracts/openapi.json`, from which `openapi-typescript`
generates `apps/web/src/types/api.generated.ts`. Hand-written types are limited
to UI helpers.

**Storage.** SQLite file under `data/` (gitignored) for the demo footprint; the
SQLAlchemy models are written so a server database is a configuration change.

**Entry points.** A root `Makefile` is the only interface humans and CI use:
`setup`, `seed`, `dev`, `api`, `web`, `test`, `lint`, `typecheck`, `build`,
`contracts`, `demo-reset`, `incident-emit`, `batch-reconcile`.

## Consequences

* One pull request can change a domain rule, its API schema, the generated
  client types and the UI, and CI validates the whole chain.
* The batch service imports the API's models and domain modules directly
  instead of duplicating them; the price is that `services/batch` cannot be
  released independently, which is acceptable for a system deployed as a unit.
* Legacy parity tests live next to the code that must honor them and run in
  the same `pytest` invocation (`legacy/reference-tests` is in `testpaths`).
* Two toolchains (uv, npm) must be installed; `scripts/setup.sh` does both.
* Version pins are deliberate and are bumped by explicit PRs (Dependabot opens
  them); floating ranges are not used for runtime dependencies.
