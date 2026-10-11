# Local development

Everything runs on your machine against a synthetic SQLite database. No network access is
needed after dependencies are installed, and nothing talks to external services.

## Prerequisites

| Tool   | Version                         | Notes                                                                 |
| ------ | ------------------------------- | --------------------------------------------------------------------- |
| uv     | 0.9 or newer                    | manages Python 3.12 and the workspace virtualenv (`.python-version`)  |
| Node   | 22 or newer (24 pinned)         | `.nvmrc` pins 24; CI runs 22 LTS. `nvm install` picks up the pin      |
| npm    | ships with Node                 | single root `package-lock.json`, workspaces under `apps/`             |
| make   | GNU Make 3.81+                  | the macOS default works; targets avoid newer-only features            |
| cobc   | GnuCOBOL 3.x (optional)         | enables COBOL execution in the legacy golden tests (`brew install gnucobol`) |

`scripts/setup.sh` checks these and prints install hints when something is missing.

## First run

```bash
make setup          # uv sync, npm ci, copies .env.example to .env
make seed           # deterministic scenario database -> data/meridian_flow.db
make dev            # API + web together, Ctrl-C stops both
```

Open http://localhost:5173. The API documentation is at http://localhost:8000/docs.

Scenario clock: the application believes it is **Wednesday 18 March 2026, 18:40 UTC**
(`MF_SCENARIO_NOW`). Countdowns, ages and "today" filters use that instant, not your clock.

## Ports and URLs

| What                | Default                          | Override                      |
| ------------------- | -------------------------------- | ----------------------------- |
| API (uvicorn)       | http://localhost:8000            | `API_PORT=8010 make api`      |
| API docs            | http://localhost:8000/docs       |                               |
| Health / readiness  | `/health`, `/ready`              |                               |
| Web (Vite)          | http://localhost:5173            | `WEB_PORT=5180 make web`      |
| Vite proxy          | `/api` -> `http://localhost:8000` | `apps/web/vite.config.ts`    |

`make ready` polls `/ready` and the web server (default timeout 90 s; `READY_TIMEOUT=180`).

## Environment

`.env.example` documents every variable; `make setup` copies it to `.env`. The application
reads `MF_*` variables through `app.core.config.Settings`:

| Variable               | Default                      | Purpose                                            |
| ---------------------- | ---------------------------- | -------------------------------------------------- |
| `MF_SCENARIO_NOW`      | `2026-03-18T18:40:00Z`       | the scenario clock                                 |
| `MF_DEMO_DEFAULT_USER` | `priya.raman`                | identity when `X-Demo-User` is absent              |
| `MF_LOG_FORMAT`        | `console`                    | `json` for structured logs                         |

`API_PORT`, `WEB_PORT`, `DB_FILE`, `UV` and `NPM` are tooling variables read by the Makefile
and `scripts/`; set them in your shell or on the `make` command line.

Demo identity is a request header, not authentication:
`curl -H 'X-Demo-User: marcus.okafor' localhost:8000/api/v1/users/me`. Unknown users get 401.

## Make targets

Run `make help` for the live list.

| Target            | Command                                                                   |
| ----------------- | ------------------------------------------------------------------------- |
| `setup`           | `scripts/setup.sh` (uv sync, npm ci, .env; `PLAYWRIGHT=1` adds Chromium)  |
| `seed`            | `uv run python -m app.seed.cli seed`                                      |
| `seed-verify`     | `uv run python -m app.seed.cli verify`                                    |
| `demo-reset`      | `scripts/demo_reset.sh` — delete `data/meridian_flow.db*` and reseed      |
| `dev`             | `scripts/dev.sh` — API and web via `concurrently`                         |
| `api`             | `uv run uvicorn app.main:app --app-dir services/api --reload --port 8000` |
| `web`             | `npm run dev -w apps/web`                                                 |
| `test`            | `test-api` then `test-web`                                                |
| `test-api`        | `uv run pytest services/api services/batch legacy/reference-tests -q`     |
| `test-web`        | `npm run test -w apps/web -- --run`                                       |
| `test-e2e`        | `npm run test:e2e -w apps/web` (API and web must be running)              |
| `lint`            | `uv run ruff check . && uv run ruff format --check . && npm run lint -w apps/web` |
| `typecheck`       | `uv run mypy services/api/app services/batch/batch && npm run typecheck -w apps/web` |
| `build`           | `npm run build -w apps/web`                                               |
| `contracts`       | `uv run python scripts/export_openapi.py && npm run generate:types -w apps/web` |
| `ready`           | `scripts/wait_for_ready.sh`                                               |
| `incident-emit`   | `uv run python scripts/emit_incident.py INC-2026-0318-004`                |
| `batch-reconcile` | `uv run python -m batch.jobs.cli reconciliation run --value-date 2026-03-17` |
| `demo-worktrees`  | `scripts/demo/create_worktrees.sh`                                        |
| `demo-branches`   | `scripts/demo/create_branches.sh`                                         |
| `clean`           | remove caches, coverage and build outputs (keeps `.venv`, `node_modules`, the DB) |

## Everyday workflows

**Backend change.** Edit under `services/api/app` or `services/batch/batch`; uvicorn reloads.
Run `make lint typecheck test-api`. If an API shape changed, run `make contracts` and commit
`shared/contracts/openapi.json` plus the regenerated `apps/web/src/types/api.generated.ts`.

**Frontend change.** Vite hot-reloads. Run `make lint typecheck test-web`; for flows, start the
stack with `make dev`, wait with `make ready`, then `make test-e2e`.

**Batch jobs.** `uv run python -m batch.jobs.cli --help`. Reconciliation can also be triggered
per batch from the API (`POST /api/v1/settlement/batches/{ref}/reconcile`).

**Fresh data.** `make demo-reset` (prompts) or `make demo-reset FORCE=1`. See
`docs/operations/demo-reset.md` for exactly what it deletes.

**Logging.** Set `MF_LOG_FORMAT=json` to get one JSON object per line with
`timestamp, level, event, logger, service, correlation_id` and request/entity fields
(`request_id, method, path, status_code, duration_ms, payment_ref, batch_ref, exception_ref`).
Every API response carries `X-Correlation-ID`; send your own value to trace a flow end to end.

**Legacy components.** `legacy/reference-tests` run in `make test-api`. With `cobc` on `PATH`
the COBOL program is compiled and executed; otherwise the Python reference is validated against
the fixtures and the COBOL step is reported as skipped.

## Troubleshooting

**Port already in use** (`[Errno 48] Address already in use` or Vite picking 5174).
Find and stop the process, or choose another port:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN      # macOS / Linux
kill <pid>
API_PORT=8010 make api                 # alternative port; update the Vite proxy target too
```

Vite moves to the next free port when 5173 is taken; `make ready` then times out on the web URL.
Either stop the other process or run `WEB_PORT=<port> make ready`.

**`/ready` returns 503 or `seeded: false`.** The database is missing or not seeded. Run
`make seed` (idempotent). If the file exists but the seed version differs or verification fails,
run `make demo-reset FORCE=1`.

**Stale or corrupted database** (`no such table`, seed version mismatch, odd counts after
local experiments). Stop the API first (an open SQLite handle keeps the old file alive on macOS),
then `make demo-reset`. The reset deletes only `data/meridian_flow.db` and its `-wal`, `-shm`,
`-journal` sidecars.

**`ModuleNotFoundError: app` or `batch` under `uv run`.** The workspace is not synced. Run
`uv sync` from the repository root; both packages are installed editable from the lockfile.

**uv picks the wrong Python.** `uv python install 3.12 && uv sync`. `.python-version` pins 3.12;
the project requires `>=3.12,<3.13`.

**Node version too old** (`engines` warning, syntax errors in tooling). `nvm install` in the repo
root uses `.nvmrc` (24). CI runs Node 22, so both work. After switching Node versions run
`rm -rf node_modules && npm ci`.

**`Extra inputs are not permitted` on startup.** `.env` contains an `MF_*` key the settings model
does not declare. Remove or comment the line; only variables listed in `.env.example` as active
are guaranteed.

**Playwright cannot find a browser.** `npx playwright install chromium` (or
`PLAYWRIGHT=1 make setup`). On Linux add `--with-deps`.

**`make demo-reset` refuses to run.** It only accepts `DB_FILE` values of the form
`data/<name>.db`, aborts when the database is open by another process (unless `FORCE=1`), and
needs either a terminal to confirm or `FORCE=1`.

**CORS or 404 from the web app for `/api/...`.** The Vite proxy forwards `/api` to
`http://localhost:8000`; make sure the API is up (`make ready --api-only` via
`bash scripts/wait_for_ready.sh --api-only`) and that `API_PORT` matches the proxy target.

**Time looks wrong in the UI.** It is the scenario clock (18:40 UTC on 2026-03-18), by design.
Change `MF_SCENARIO_NOW` in `.env` and restart the API to move the scenario.

## Editor setup

`.vscode/extensions.json` recommends Ruff, Pylance, mypy, ESLint, Prettier, Tailwind CSS,
Playwright, EditorConfig, YAML and a COBOL syntax extension; `.vscode/settings.json` points the
Python extension at `.venv`, formats Python with Ruff and TypeScript with Prettier on save, and
keeps tabs in the Makefile. Cursor users get the same through `.cursor/`.
