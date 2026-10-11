# Meridian Flow — developer entry points.
#
# Compatible with GNU Make 3.81 (the macOS default). Run `make help` for the target list.
# The target contract is documented in docs/operations/local-development.md.
#
# Variables can be overridden on the command line or in the environment:
#   make api API_PORT=8010
#   UV=~/.local/bin/uv make test-api

UV ?= uv
NPM ?= npm
API_PORT ?= 8000
WEB_PORT ?= 5173
DB_FILE := data/meridian_flow.db
READY_TIMEOUT ?= 90

export UV NPM API_PORT WEB_PORT DB_FILE

.DEFAULT_GOAL := help

.PHONY: help setup seed seed-verify demo-reset dev api web test test-api test-web test-e2e \
        lint typecheck build contracts ready incident-emit batch-reconcile demo-worktrees \
        demo-branches clean

help: ## Show this help
	@echo "Meridian Flow — make targets"
	@echo
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Variables: UV=$(UV) NPM=$(NPM) API_PORT=$(API_PORT) WEB_PORT=$(WEB_PORT) DB_FILE=$(DB_FILE)"

# ---------------------------------------------------------------------------
# Setup and data
# ---------------------------------------------------------------------------

setup: ## Install Python (uv sync) and Node (npm ci) deps, create .env; PLAYWRIGHT=1 adds browsers
	@bash scripts/setup.sh

seed: ## Seed the synthetic scenario database (idempotent; skips if already seeded)
	$(UV) run python -m app.seed.cli seed

seed-verify: ## Re-derive the seed invariants; exits non-zero on any violation
	$(UV) run python -m app.seed.cli verify

demo-reset: ## Delete data/meridian_flow.db* after confirmation (or FORCE=1) and reseed
	@bash scripts/demo_reset.sh

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

dev: ## Run the API and the web dev server together
	@bash scripts/dev.sh

api: ## Run the FastAPI app with auto-reload (API_PORT, default 8000)
	$(UV) run uvicorn app.main:app --app-dir services/api --reload --port $(API_PORT)

web: ## Run the Vite dev server (WEB_PORT, default 5173; proxies /api to the API)
	$(NPM) run dev -w apps/web

ready: ## Wait until the API /ready endpoint and the web server respond (READY_TIMEOUT=90)
	@bash scripts/wait_for_ready.sh $(READY_TIMEOUT)

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

test: test-api test-web ## Run backend and frontend test suites

test-api: ## pytest for the API, batch jobs and legacy reference tests
	$(UV) run pytest services/api services/batch legacy/reference-tests -q

test-web: ## vitest, single run
	$(NPM) run test -w apps/web -- --run

test-e2e: ## Playwright end-to-end tests (expects API and web to be running; see `make ready`)
	$(NPM) run test:e2e -w apps/web

lint: ## ruff check + ruff format --check + eslint
	$(UV) run ruff check . && $(UV) run ruff format --check . && $(NPM) run lint -w apps/web

typecheck: ## mypy (api + batch) and tsc --noEmit
	$(UV) run mypy services/api/app services/batch/batch && $(NPM) run typecheck -w apps/web

build: ## Production build of the web app
	$(NPM) run build -w apps/web

contracts: ## Export OpenAPI to shared/contracts/openapi.json and regenerate TypeScript types
	$(UV) run python scripts/export_openapi.py && $(NPM) run generate:types -w apps/web

# ---------------------------------------------------------------------------
# Operations and demo helpers
# ---------------------------------------------------------------------------

incident-emit: ## Print the INC-2026-0318-004 incident payload with its evidence summary
	$(UV) run python scripts/emit_incident.py INC-2026-0318-004

batch-reconcile: ## Run the baseline daily reconciliation for value date 2026-03-17
	$(UV) run python -m batch.jobs.cli reconciliation run --value-date 2026-03-17

demo-worktrees: ## Create git worktrees for the demo/* branches that exist (../meridian-flow-worktrees)
	@bash scripts/demo/create_worktrees.sh

demo-branches: ## Create the demo/* branches from the baseline-v1 tag if they are missing
	@bash scripts/demo/create_branches.sh

clean: ## Remove caches, coverage and build outputs (keeps .venv, node_modules and the database)
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml
	rm -rf apps/web/dist apps/web/coverage apps/web/test-results apps/web/playwright-report apps/web/blob-report apps/web/.vite
	rm -rf legacy/cobol/build
	find . -type d -name __pycache__ -not -path './node_modules/*' -not -path './.venv/*' -prune -exec rm -rf {} +
