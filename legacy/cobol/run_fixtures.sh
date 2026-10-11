#!/usr/bin/env bash
# Run the golden fixtures through the compiled FEECALC01 binary.
#
#   1. converts legacy/reference-tests/fixtures/feecalc_cases.json -> build/feecalc_cases.FEEIN
#   2. runs build/feecalc01 with DD_FEEIN / DD_FEEOUT pointing at the build directory
#   3. prints FEEOUT and a per-record comparison against expected_fee / band / cap flag
#
# Usage:  bash legacy/cobol/run_fixtures.sh [path/to/cases.json]
# Exit:   0 all records match, 1 mismatch, 2 cobc/python not available.
#
# The record encoder/decoder is the one in app.integrations.legacy.feecalc so the
# layout is defined exactly once; the script therefore runs Python through `uv`
# from the repository root (falls back to python3 with PYTHONPATH=services/api).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
BIN="${HERE}/build/feecalc01"
WORK="${HERE}/build"
CASES="${1:-${ROOT}/legacy/reference-tests/fixtures/feecalc_cases.json}"
FEEIN="${WORK}/feecalc_cases.FEEIN"
FEEOUT="${WORK}/feecalc_cases.FEEOUT"

if [[ ! -x "${BIN}" ]]; then
  bash "${HERE}/build.sh"
fi

if command -v uv >/dev/null 2>&1; then
  PY=(uv run --project "${ROOT}" python)
elif command -v python3 >/dev/null 2>&1; then
  export PYTHONPATH="${ROOT}/services/api${PYTHONPATH:+:${PYTHONPATH}}"
  PY=(python3)
else
  echo "run_fixtures.sh: neither uv nor python3 found" >&2
  exit 2
fi

mkdir -p "${WORK}"
echo "run_fixtures.sh: encoding $(basename "${CASES}") -> ${FEEIN}"
"${PY[@]}" - "${CASES}" "${FEEIN}" <<'PY'
import json
import sys
from decimal import Decimal
from pathlib import Path

from app.integrations.legacy.feecalc import encode_feein_record

cases = json.loads(Path(sys.argv[1]).read_text())["cases"]
lines = [encode_feein_record(Decimal(c["amount"]), c["segment"], c["rail"]) for c in cases]
Path(sys.argv[2]).write_text("\n".join(lines) + "\n")
print(f"run_fixtures.sh: {len(lines)} FEEIN records written")
PY

echo "run_fixtures.sh: running FEECALC01"
set +e
DD_FEEIN="${FEEIN}" DD_FEEOUT="${FEEOUT}" "${BIN}"
RC=$?
set -e
echo "run_fixtures.sh: FEECALC01 RETURN-CODE=${RC}"

echo
echo "---- FEEOUT (${FEEOUT}) ----"
cat "${FEEOUT}"
echo "----------------------------"
echo

"${PY[@]}" - "${CASES}" "${FEEOUT}" <<'PY'
import json
import sys
from decimal import Decimal
from pathlib import Path

from app.integrations.legacy.feecalc import parse_feeout_record

cases = json.loads(Path(sys.argv[1]).read_text())["cases"]
records = [parse_feeout_record(line) for line in Path(sys.argv[2]).read_text().splitlines() if line]
if len(records) != len(cases):
    print(f"MISMATCH: {len(records)} FEEOUT records for {len(cases)} cases")
    sys.exit(1)

fails = 0
print(f"{'id':6} {'amount':>18} seg rail  {'cobol':>9} {'expected':>9} band cap  result")
for case, rec in zip(cases, records, strict=True):
    expected = Decimal(case["expected_fee"])
    ok = (
        rec.fee == expected
        and rec.band == case["expected_band"]
        and rec.capped is case["expected_capped"]
        and rec.status_code == "00"
    )
    fails += 0 if ok else 1
    print(
        f"{case['id']:6} {case['amount']:>18} {case['segment']:^3} {case['rail']:<5} "
        f"{rec.fee:>9} {expected:>9}  {rec.band}   {'Y' if rec.capped else 'N'}   "
        f"{'PASS' if ok else 'FAIL'}"
    )
print()
print(f"run_fixtures.sh: {len(cases) - fails}/{len(cases)} records match the golden fixtures")
sys.exit(1 if fails else 0)
PY
