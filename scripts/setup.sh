#!/usr/bin/env bash
# Meridian Flow — one-shot developer setup.
#
# Usage:
#   scripts/setup.sh                 (or: make setup)
#   PLAYWRIGHT=1 scripts/setup.sh    also installs the Playwright Chromium browser for e2e tests
#
# What it does, in order:
#   1. checks that uv, node and npm are installed (with helpful install hints)
#   2. makes sure the pinned Python (see .python-version) is available to uv
#   3. uv sync                       -> .venv with the API, batch and dev dependencies
#   4. npm ci (or npm install when no lockfile exists yet)
#   5. copies .env.example to .env if .env is missing
#   6. optionally installs the Playwright browser
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UV_BIN="${UV:-uv}"
NPM_BIN="${NPM:-npm}"
REQUIRED_NODE_MAJOR=22
PYTHON_VERSION="$(tr -d '[:space:]' < .python-version 2>/dev/null || true)"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[1;32mok\033[0m  %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

say "Checking prerequisites"

if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  fail "uv not found. Install it with 'brew install uv' or 'curl -LsSf https://astral.sh/uv/install.sh | sh', then re-run."
fi
ok "uv $("$UV_BIN" --version | awk '{print $2}')"

if ! command -v node >/dev/null 2>&1; then
  fail "node not found. Install Node ${REQUIRED_NODE_MAJOR}+ (this repo pins $(cat .nvmrc 2>/dev/null || echo 24) in .nvmrc; 'nvm install' or 'brew install node')."
fi
NODE_VERSION="$(node --version)"
NODE_MAJOR="${NODE_VERSION#v}"
NODE_MAJOR="${NODE_MAJOR%%.*}"
if [ "$NODE_MAJOR" -lt "$REQUIRED_NODE_MAJOR" ]; then
  fail "Node ${NODE_VERSION} is too old; Node ${REQUIRED_NODE_MAJOR}+ is required (.nvmrc pins $(cat .nvmrc 2>/dev/null || echo 24)). Try 'nvm install' in the repo root."
fi
ok "node ${NODE_VERSION}"

if ! command -v "$NPM_BIN" >/dev/null 2>&1; then
  fail "npm not found. It normally ships with Node; reinstall Node or run 'corepack enable npm'."
fi
ok "npm $("$NPM_BIN" --version)"

say "Ensuring Python ${PYTHON_VERSION} is available to uv"
if PY_PATH="$("$UV_BIN" python find "$PYTHON_VERSION" 2>/dev/null)"; then
  ok "python ${PYTHON_VERSION} at ${PY_PATH}"
else
  note "python ${PYTHON_VERSION} not found; installing it with uv (managed, no system changes)"
  "$UV_BIN" python install "$PYTHON_VERSION"
  ok "installed python ${PYTHON_VERSION}"
fi

say "Syncing the Python workspace (uv sync)"
"$UV_BIN" sync
ok "python environment ready in .venv"

say "Installing Node workspace dependencies"
if [ -f package-lock.json ]; then
  "$NPM_BIN" ci
  ok "npm ci complete"
else
  note "package-lock.json not found; running 'npm install' (this creates the lockfile)"
  "$NPM_BIN" install
  ok "npm install complete"
fi

say "Environment file"
if [ -f .env ]; then
  ok ".env already exists (left untouched)"
else
  cp .env.example .env
  ok "created .env from .env.example"
fi

mkdir -p data

if [ "${PLAYWRIGHT:-0}" = "1" ]; then
  say "Installing the Playwright Chromium browser (PLAYWRIGHT=1)"
  npx playwright install chromium
  ok "playwright chromium installed"
else
  say "Playwright"
  note "skipped browser download; run 'PLAYWRIGHT=1 scripts/setup.sh' or 'npx playwright install chromium' before 'make test-e2e'"
fi

cat <<EOF

Setup complete. Next steps:

  make seed        build the synthetic scenario database at data/meridian_flow.db
  make dev         run the API (http://localhost:${API_PORT:-8000}) and the web app (http://localhost:${WEB_PORT:-5173})
  make test        backend and frontend tests
  make help        list every target

Details: docs/operations/local-development.md
EOF
