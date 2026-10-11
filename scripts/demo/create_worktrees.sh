#!/usr/bin/env bash
# Meridian Flow — create git worktrees for the demo branches.
#
# Each demo branch that exists (locally or on the remote) gets its own working copy under
#   ../meridian-flow-worktrees/<branch-short-name>      e.g. ../meridian-flow-worktrees/local-agent-start
# so presenters can switch segments without touching the main checkout. Branches that do not
# exist are skipped (run scripts/demo/create_branches.sh first). Nothing is ever deleted or
# force-updated; `--remove` detaches only the worktrees this script manages, after confirmation,
# and never deletes branches.
#
# Usage:
#   scripts/demo/create_worktrees.sh            create missing worktrees, print the table
#   scripts/demo/create_worktrees.sh --list     print the table only
#   scripts/demo/create_worktrees.sh --remove   remove the managed worktrees (asks for 'y'; FORCE=1 skips)
#   WORKTREE_ROOT=/path scripts/demo/create_worktrees.sh      override the parent directory
set -euo pipefail

REMOTE="${REMOTE:-origin}"
MODE=create
for arg in "$@"; do
  case "$arg" in
    --list) MODE=list ;;
    --remove) MODE=remove ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'error: unknown argument %s (see --help)\n' "$arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { printf 'error: not inside a git repository\n' >&2; exit 2; }
cd "$REPO_ROOT"
WORKTREE_ROOT="${WORKTREE_ROOT:-$(dirname "$REPO_ROOT")/meridian-flow-worktrees}"

BRANCHES=(
  demo/local-agent-start
  demo/local-agent-completed
  demo/cloud-agent-start
  demo/cloud-agent-completed
  demo/mgb-407-cutoff-regression
  demo/incident-investigation
)

local_exists()  { git show-ref --verify --quiet "refs/heads/$1"; }
remote_exists() { git show-ref --verify --quiet "refs/remotes/$REMOTE/$1"; }
short_name()    { printf '%s' "${1#demo/}"; }
registered()    { git worktree list --porcelain | grep -Fxq "worktree $1"; }
head_of()       { git -C "$1" rev-parse --short HEAD 2>/dev/null || echo "-"; }

ROWS=()
add_row() { ROWS+=("$(printf '%-34s %-46s %-10s %s' "$1" "$2" "$3" "$4")"); }

print_table() {
  printf '\n%-34s %-46s %-10s %s\n' "BRANCH" "WORKTREE" "STATE" "HEAD"
  printf '%-34s %-46s %-10s %s\n' "------" "--------" "-----" "----"
  for row in "${ROWS[@]}"; do printf '%s\n' "$row"; done
  printf '\nworktree root: %s\n' "$WORKTREE_ROOT"
}

if [ "$MODE" = "remove" ]; then
  targets=()
  for b in "${BRANCHES[@]}"; do
    path="$WORKTREE_ROOT/$(short_name "$b")"
    if registered "$path"; then targets+=("$path"); fi
  done
  if [ "${#targets[@]}" -eq 0 ]; then
    printf 'no managed worktrees registered under %s; nothing to do.\n' "$WORKTREE_ROOT"
    exit 0
  fi
  printf 'The following worktrees will be removed (branches are kept):\n'
  for t in "${targets[@]}"; do printf '  %s\n' "$t"; done
  if [ "${FORCE:-0}" != "1" ]; then
    if [ ! -t 0 ]; then printf 'error: no terminal for confirmation; set FORCE=1 to proceed\n' >&2; exit 3; fi
    printf "Type 'y' to continue: "
    read -r answer
    [ "$answer" = "y" ] || { printf 'aborted; nothing removed.\n'; exit 3; }
  fi
  for t in "${targets[@]}"; do
    # No --force: a worktree with uncommitted changes is left in place and reported.
    if out="$(git worktree remove "$t" 2>&1)"; then
      printf 'removed  %s\n' "$t"
    else
      printf 'kept     %s (%s)\n' "$t" "$(printf '%s' "$out" | head -n 1)"
    fi
  done
  git worktree prune
  exit 0
fi

mkdir -p "$WORKTREE_ROOT"
for b in "${BRANCHES[@]}"; do
  short="$(short_name "$b")"
  path="$WORKTREE_ROOT/$short"
  if registered "$path"; then
    add_row "$b" "$path" "present" "$(head_of "$path")"
    continue
  fi
  if [ "$MODE" = "list" ]; then
    if local_exists "$b" || remote_exists "$b"; then
      add_row "$b" "$path" "absent" "-"
    else
      add_row "$b" "$path" "no-branch" "-"
    fi
    continue
  fi
  if [ -e "$path" ]; then
    add_row "$b" "$path" "blocked" "path exists but is not a registered worktree"
    continue
  fi
  if local_exists "$b"; then
    if out="$(git worktree add "$path" "$b" 2>&1)"; then
      add_row "$b" "$path" "created" "$(head_of "$path")"
    else
      add_row "$b" "$path" "failed" "$(printf '%s' "$out" | tail -n 1)"
    fi
  elif remote_exists "$b"; then
    if out="$(git worktree add --track -b "$b" "$path" "$REMOTE/$b" 2>&1)"; then
      add_row "$b" "$path" "created" "$(head_of "$path")"
    else
      add_row "$b" "$path" "failed" "$(printf '%s' "$out" | tail -n 1)"
    fi
  else
    add_row "$b" "$path" "skipped" "branch does not exist (run scripts/demo/create_branches.sh)"
  fi
done

print_table
