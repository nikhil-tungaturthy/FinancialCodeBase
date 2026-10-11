#!/usr/bin/env bash
# Compile FEECALC01 with GnuCOBOL into legacy/cobol/build/feecalc01 (gitignored).
#
# Usage:  bash legacy/cobol/build.sh            # uses `cobc` from PATH
#         COBC=/opt/homebrew/bin/cobc bash legacy/cobol/build.sh
#
# Exit codes: 0 compiled, 2 cobc not found, otherwise cobc's own exit code.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COBC="${COBC:-cobc}"
OUT_DIR="${HERE}/build"
OUT_BIN="${OUT_DIR}/feecalc01"

if ! command -v "${COBC}" >/dev/null 2>&1; then
  echo "build.sh: GnuCOBOL compiler '${COBC}' not found on PATH (set COBC=/path/to/cobc)." >&2
  exit 2
fi

mkdir -p "${OUT_DIR}"
echo "build.sh: $("${COBC}" --version | head -n 1)"
echo "build.sh: compiling FEECALC01.cbl -> ${OUT_BIN}"
"${COBC}" -x -std=default -Wall \
  -I "${HERE}/copybooks" \
  -o "${OUT_BIN}" \
  "${HERE}/FEECALC01.cbl"
echo "build.sh: ok"
