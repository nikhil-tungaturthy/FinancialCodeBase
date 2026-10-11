#!/usr/bin/env bash
# Meridian Flow — wait until the API readiness endpoint and the web dev server respond.
#
# Usage:
#   scripts/wait_for_ready.sh [TIMEOUT_SECONDS] [--api-only | --web-only]     (default timeout: 90)
#
# Environment:
#   API_PORT / WEB_PORT   ports to probe (default 8000 / 5173)
#   API_URL  / WEB_URL    full URLs to probe (override the port-based defaults)
#   READY_INTERVAL        seconds between probes (default 1)
#
# Exit status: 0 when every requested endpoint responded with HTTP 2xx/3xx, 1 on timeout,
# 2 on usage errors or when curl is missing.
set -euo pipefail

TIMEOUT=90
MODE=both
for arg in "$@"; do
  case "$arg" in
    --api-only) MODE=api ;;
    --web-only) MODE=web ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    ''|*[!0-9]*) printf 'error: unexpected argument %s\n' "$arg" >&2; exit 2 ;;
    *) TIMEOUT="$arg" ;;
  esac
done

command -v curl >/dev/null 2>&1 || { printf 'error: curl is required\n' >&2; exit 2; }

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
API_URL="${API_URL:-http://localhost:${API_PORT}/ready}"
WEB_URL="${WEB_URL:-http://localhost:${WEB_PORT}}"
INTERVAL="${READY_INTERVAL:-1}"

probe() { curl -fsS --max-time 3 -o /dev/null "$1" 2>/dev/null; }

api_ready=0
web_ready=0
[ "$MODE" = "web" ] && api_ready=1
[ "$MODE" = "api" ] && web_ready=1

start="$(date +%s)"
last_report=0
printf 'waiting up to %ss for' "$TIMEOUT"
[ "$MODE" != "web" ] && printf ' api=%s' "$API_URL"
[ "$MODE" != "api" ] && printf ' web=%s' "$WEB_URL"
printf '\n'

while :; do
  now="$(date +%s)"
  elapsed=$((now - start))

  if [ "$api_ready" -eq 0 ] && probe "$API_URL"; then
    api_ready=1
    printf 'ready  api  %s (%ss)\n' "$API_URL" "$elapsed"
    body="$(curl -fsS --max-time 3 "$API_URL" 2>/dev/null || true)"
    [ -n "$body" ] && printf '       %s\n' "$body"
  fi
  if [ "$web_ready" -eq 0 ] && probe "$WEB_URL"; then
    web_ready=1
    printf 'ready  web  %s (%ss)\n' "$WEB_URL" "$elapsed"
  fi

  if [ "$api_ready" -eq 1 ] && [ "$web_ready" -eq 1 ]; then
    printf 'all endpoints ready after %ss\n' "$elapsed"
    exit 0
  fi

  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    printf 'timeout after %ss:' "$elapsed" >&2
    [ "$api_ready" -eq 0 ] && printf ' api not ready (%s)' "$API_URL" >&2
    [ "$web_ready" -eq 0 ] && printf ' web not ready (%s)' "$WEB_URL" >&2
    printf '\n' >&2
    exit 1
  fi

  if [ $((elapsed - last_report)) -ge 10 ]; then
    last_report="$elapsed"
    printf '...still waiting (%ss)\n' "$elapsed"
  fi
  sleep "$INTERVAL"
done
