#!/usr/bin/env bash
# Meridian Flow — reset the local demo database and rebuild it from the deterministic seed.
#
# Usage:
#   scripts/demo_reset.sh              interactive: prints a warning and asks for 'y'
#   FORCE=1 scripts/demo_reset.sh      non-interactive (make demo-reset FORCE=1, CI)
#   scripts/demo_reset.sh --force      same as FORCE=1
#
# Scope, deliberately narrow:
#   * deletes ONLY data/meridian_flow.db and its SQLite sidecars (-wal, -shm, -journal)
#   * refuses any DB_FILE that is not a plain *.db path directly inside data/
#   * never touches source files, .env, node_modules, .venv, fixtures or git state
#   * then runs `uv run python -m app.seed.cli seed` and `... verify`
# See docs/operations/demo-reset.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UV_BIN="${UV:-uv}"
DB_FILE="${DB_FILE:-data/meridian_flow.db}"
FORCE="${FORCE:-0}"

usage() {
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

fail() { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit "${2:-1}"; }

for arg in "$@"; do
  case "$arg" in
    --force|-y|--yes) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument '$arg' (use --force or -h)" 2 ;;
  esac
done

# --- Safety checks on the target path -------------------------------------------------------
case "$DB_FILE" in
  data/*.db) ;;
  *) fail "refusing to continue: DB_FILE must be a .db file directly inside data/ (got '$DB_FILE')" 2 ;;
esac
case "$DB_FILE" in
  *..*|*/./*|data/*/*) fail "refusing to continue: DB_FILE must be a plain path such as data/meridian_flow.db (got '$DB_FILE')" 2 ;;
esac

DATA_DIR="$REPO_ROOT/data"
mkdir -p "$DATA_DIR"
DATA_REAL="$(cd "$DATA_DIR" && pwd -P)"
PARENT_REAL="$(cd "$(dirname "$REPO_ROOT/$DB_FILE")" && pwd -P)"
if [ "$PARENT_REAL" != "$DATA_REAL" ]; then
  fail "refusing to continue: $DB_FILE does not resolve inside $DATA_DIR" 2
fi

DB_ABS="$DATA_REAL/$(basename "$DB_FILE")"
TARGETS=("$DB_ABS" "$DB_ABS-wal" "$DB_ABS-shm" "$DB_ABS-journal")

# --- Warning box ------------------------------------------------------------------------------
LINES=(
  "WARNING: demo reset will DELETE the local scenario database"
  ""
  "  $DB_ABS"
  "  (and its SQLite sidecars: -wal, -shm, -journal, when present)"
  ""
  "Nothing outside $DATA_DIR is touched."
  "Afterwards the database is rebuilt with the deterministic seed:"
  "  $UV_BIN run python -m app.seed.cli seed"
  "  $UV_BIN run python -m app.seed.cli verify"
)
width=0
for l in "${LINES[@]}"; do
  [ "${#l}" -gt "$width" ] && width="${#l}"
done
border="+$(printf '%*s' $((width + 2)) '' | tr ' ' '-')+"
printf '\033[1;33m%s\033[0m\n' "$border"
for l in "${LINES[@]}"; do
  printf '\033[1;33m|\033[0m %-*s \033[1;33m|\033[0m\n' "$width" "$l"
done
printf '\033[1;33m%s\033[0m\n' "$border"

# --- Open-file check (advisory; FORCE overrides) ----------------------------------------------
if command -v lsof >/dev/null 2>&1 && [ -e "$DB_ABS" ]; then
  if open_pids="$(lsof -t -- "$DB_ABS" 2>/dev/null)" && [ -n "$open_pids" ]; then
    printf '\033[1;33mnote:\033[0m the database is currently open by PID(s): %s\n' "$(echo "$open_pids" | tr '\n' ' ')"
    printf '      Stop "make dev" / "make api" first so the API reopens the fresh file.\n'
    if [ "$FORCE" != "1" ]; then
      fail "aborting while the database is open (re-run with FORCE=1 to override)" 3
    fi
  fi
fi

# --- Confirmation -----------------------------------------------------------------------------
if [ "$FORCE" = "1" ]; then
  printf 'FORCE=1 set; continuing without prompt.\n'
elif [ -t 0 ]; then
  printf "Type 'y' to continue, anything else to abort: "
  read -r answer
  if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
    printf 'Aborted; nothing was deleted.\n'
    exit 3
  fi
else
  fail "no interactive terminal and FORCE is not set; re-run with FORCE=1 to confirm" 3
fi

# --- Delete -----------------------------------------------------------------------------------
removed=0
for f in "${TARGETS[@]}"; do
  if [ -e "$f" ]; then
    rm -f -- "$f"
    printf 'removed  %s\n' "$f"
    removed=$((removed + 1))
  fi
done
if [ "$removed" -eq 0 ]; then
  printf 'nothing to remove (no database present at %s)\n' "$DB_ABS"
fi

# --- Reseed and verify ------------------------------------------------------------------------
printf '\n==> %s run python -m app.seed.cli seed\n' "$UV_BIN"
"$UV_BIN" run python -m app.seed.cli seed
printf '\n==> %s run python -m app.seed.cli verify\n' "$UV_BIN"
"$UV_BIN" run python -m app.seed.cli verify
printf '\nDemo database reset complete: %s\n' "$DB_ABS"
