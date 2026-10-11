#!/usr/bin/env bash
# Meridian Flow — create the demo branches from the baseline tag.
#
# The demo segments start from fixed branches that all fork from the `baseline-v1` tag
# (the verified baseline commit on main). This script creates any that are missing and
# leaves existing ones untouched. It never force-pushes, never deletes and never checks
# anything out; pushing is opt-in.
#
# Usage:
#   scripts/demo/create_branches.sh              create missing branches locally
#   scripts/demo/create_branches.sh --list       show the branch table only
#   scripts/demo/create_branches.sh --dry-run    print what would be created
#   scripts/demo/create_branches.sh --push       also `git push -u origin <branch>` (fast-forward only)
#   BASE_TAG=baseline-v1 REMOTE=origin           environment overrides
#
# Branches (see SPEC §14 / docs/product/tickets):
#   demo/local-agent-start           starting point for the local-agent segment (MGB-142)
#   demo/local-agent-completed       reference result of the local-agent segment (MGB-142)
#   demo/cloud-agent-start           starting point for the cloud-agent segment (MGB-318)
#   demo/cloud-agent-completed       reference result of the cloud-agent segment (MGB-318)
#   demo/mgb-407-cutoff-regression   branch carrying the MGB-407 change for the review segment
#   demo/incident-investigation      working branch for the MGB-502 incident investigation
set -euo pipefail

BASE_TAG="${BASE_TAG:-baseline-v1}"
REMOTE="${REMOTE:-origin}"
DO_PUSH=0
DRY_RUN=0
LIST_ONLY=0

BRANCHES=(
  demo/local-agent-start
  demo/local-agent-completed
  demo/cloud-agent-start
  demo/cloud-agent-completed
  demo/mgb-407-cutoff-regression
  demo/incident-investigation
)

describe() {
  case "$1" in
    demo/local-agent-start) echo "local-agent segment start (MGB-142)" ;;
    demo/local-agent-completed) echo "local-agent segment reference result (MGB-142)" ;;
    demo/cloud-agent-start) echo "cloud-agent segment start (MGB-318)" ;;
    demo/cloud-agent-completed) echo "cloud-agent segment reference result (MGB-318)" ;;
    demo/mgb-407-cutoff-regression) echo "review segment branch (MGB-407)" ;;
    demo/incident-investigation) echo "incident investigation working branch (MGB-502)" ;;
    *) echo "" ;;
  esac
}

usage() { sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
fail() { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit "${2:-1}"; }

for arg in "$@"; do
  case "$arg" in
    --push) DO_PUSH=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --list) LIST_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument '$arg' (see --help)" 2 ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "not inside a git repository" 2
cd "$REPO_ROOT"

local_exists()  { git show-ref --verify --quiet "refs/heads/$1"; }
remote_exists() { git show-ref --verify --quiet "refs/remotes/$REMOTE/$1"; }
short_sha()     { git rev-parse --short "$1" 2>/dev/null || echo "-"; }

if ! git rev-parse -q --verify "refs/tags/${BASE_TAG}^{commit}" >/dev/null; then
  if [ "$LIST_ONLY" -eq 1 ]; then
    printf 'note: tag %s does not exist yet; listing only.\n' "$BASE_TAG"
  else
    fail "tag '$BASE_TAG' not found. Create the baseline tag first, e.g.:  git tag -a $BASE_TAG -m 'Meridian Flow baseline v1' <commit>" 2
  fi
fi

print_table() {
  printf '\n%-34s %-10s %-9s %s\n' "BRANCH" "STATE" "HEAD" "PURPOSE"
  printf '%-34s %-10s %-9s %s\n' "------" "-----" "----" "-------"
  for b in "${BRANCHES[@]}"; do
    if local_exists "$b"; then
      state="local"; head="$(short_sha "refs/heads/$b")"
    elif remote_exists "$b"; then
      state="remote"; head="$(short_sha "refs/remotes/$REMOTE/$b")"
    else
      state="missing"; head="-"
    fi
    printf '%-34s %-10s %-9s %s\n' "$b" "$state" "$head" "$(describe "$b")"
  done
  printf '\nbase tag: %s (%s)\n' "$BASE_TAG" "$(short_sha "refs/tags/$BASE_TAG")"
}

if [ "$LIST_ONLY" -eq 1 ]; then
  print_table
  exit 0
fi

created=0
for b in "${BRANCHES[@]}"; do
  if local_exists "$b"; then
    printf 'exists   %-34s %s\n' "$b" "$(short_sha "refs/heads/$b")"
  elif remote_exists "$b"; then
    if [ "$DRY_RUN" -eq 1 ]; then
      printf 'would    %-34s track %s/%s\n' "$b" "$REMOTE" "$b"
    else
      git branch --track "$b" "$REMOTE/$b" >/dev/null
      printf 'tracked  %-34s from %s/%s\n' "$b" "$REMOTE" "$b"
      created=$((created + 1))
    fi
  else
    if [ "$DRY_RUN" -eq 1 ]; then
      printf 'would    %-34s create from %s\n' "$b" "$BASE_TAG"
    else
      git branch "$b" "refs/tags/$BASE_TAG" >/dev/null
      printf 'created  %-34s from %s (%s)\n' "$b" "$BASE_TAG" "$(short_sha "refs/heads/$b")"
      created=$((created + 1))
    fi
  fi
done

if [ "$DO_PUSH" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  git remote get-url "$REMOTE" >/dev/null 2>&1 || fail "remote '$REMOTE' is not configured; cannot push" 2
  for b in "${BRANCHES[@]}"; do
    if local_exists "$b"; then
      # Plain push: rejected (not forced) if the remote branch has diverged.
      git push --set-upstream "$REMOTE" "refs/heads/$b:refs/heads/$b"
    fi
  done
fi

print_table
if [ "$DRY_RUN" -eq 1 ]; then
  printf '\ndry run: nothing was changed.\n'
else
  printf '\n%d branch(es) created or tracked; none modified or deleted.\n' "$created"
fi
