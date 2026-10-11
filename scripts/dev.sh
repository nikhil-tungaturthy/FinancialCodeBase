#!/usr/bin/env bash
# Meridian Flow — run the API (uvicorn with reload) and the web dev server (Vite) side by side.
#
# Usage:
#   scripts/dev.sh                     (or: make dev)
#   API_PORT=8010 WEB_PORT=5180 scripts/dev.sh
#
# Uses `concurrently` (npm dev dependency) for prefixed, coloured output when it is installed;
# otherwise falls back to plain background processes. Ctrl-C stops both servers either way.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UV_BIN="${UV:-uv}"
NPM_BIN="${NPM:-npm}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

fail() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

command -v "$UV_BIN" >/dev/null 2>&1 || fail "uv not found; run 'make setup' first."
command -v "$NPM_BIN" >/dev/null 2>&1 || fail "npm not found; run 'make setup' first."
[ -d node_modules ] || fail "node_modules is missing; run 'make setup' first."
[ -d .venv ] || fail ".venv is missing; run 'make setup' first."
[ -f .env ] || printf '\033[1;33mnote:\033[0m .env not found; defaults apply (copy .env.example to .env to customise).\n'
if [ ! -f "${DB_FILE:-data/meridian_flow.db}" ]; then
  printf '\033[1;33mnote:\033[0m %s does not exist yet; run '"'"'make seed'"'"' in another terminal once the API is up.\n' "${DB_FILE:-data/meridian_flow.db}"
fi

API_CMD=("$UV_BIN" run uvicorn app.main:app --app-dir services/api --reload --port "$API_PORT")
WEB_CMD=("$NPM_BIN" run dev -w apps/web)
if [ "$WEB_PORT" != "5173" ]; then
  WEB_CMD+=(-- --port "$WEB_PORT")
fi

PIDS=()
cleanup() {
  local status=$?
  trap - INT TERM EXIT
  if [ "${#PIDS[@]}" -gt 0 ]; then
    printf '\n[dev] stopping api and web...\n'
    for pid in "${PIDS[@]}"; do
      kill -TERM "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
      wait "$pid" 2>/dev/null || true
    done
  fi
  exit "$status"
}
trap cleanup INT TERM EXIT

printf '[dev] api  -> http://localhost:%s   (docs at /docs)\n' "$API_PORT"
printf '[dev] web  -> http://localhost:%s\n' "$WEB_PORT"

if npx --no-install concurrently --version >/dev/null 2>&1; then
  npx --no-install concurrently \
    --kill-others \
    --names "api,web" \
    --prefix-colors "cyan,magenta" \
    --prefix "[{name}]" \
    "${API_CMD[*]}" \
    "${WEB_CMD[*]}" &
  PIDS+=("$!")
  wait "${PIDS[0]}"
else
  printf '[dev] concurrently is not installed; running both processes directly.\n'
  (
    "${API_CMD[@]}" 2>&1 | while IFS= read -r line; do printf '[api] %s\n' "$line"; done
  ) &
  PIDS+=("$!")
  (
    "${WEB_CMD[@]}" 2>&1 | while IFS= read -r line; do printf '[web] %s\n' "$line"; done
  ) &
  PIDS+=("$!")
  wait
fi
