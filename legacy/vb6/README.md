# modExceptionRouting - Payments Review Desk routing (VB6)

The Payments Review Desk (PRD32) was a Visual Basic 6 client used by the
operations team from 1999 until it was retired. When the mainframe hold extract
(`HOLDXTRT`) delivered a held payment, the desk called
`modExceptionRouting.RouteException` to decide three things that still drive
the modern workbench:

* the **review queue** the exception lands in (`RETAIL-STD`, `CORP-STD`,
  `INST-HV`, `FCR-SCREEN`),
* its initial **severity** (1 low ... 4 critical), and
* whether a **supervisor** must sign off before any release action.

| File | Purpose |
|---|---|
| `modExceptionRouting.bas` | The routing module: constants, `Public Type RoutingResult`, `Public Function RouteException`, the per-code severity and text tables. All rules live here. |
| `frmReviewQueue.frm` | The analyst dialog that calls `RouteException` (reason combo, USD amount, segment combo, result panel). Thin UI; no rules. |

## Behavior of `RouteException(reasonCode, amountUsd, segment)`

Inputs are trimmed and upper-cased first. Then, in this order:

| Step | Rule | Result |
|---|---|---|
| 1 | reason is `R07` (screening hit) | queue `FCR-SCREEN`, severity forced to 4, supervisor required - regardless of amount or segment |
| 2 | segment `I` and amount >= 250,000 USD | queue `INST-HV` |
| 3 | segment `R` | queue `RETAIL-STD` |
| 4 | anything else (`C`, institutional below the threshold, unknown segment) | queue `CORP-STD` (the `Case Else`) |
| 5 | severity >= 3 **or** amount >= 100,000 USD | supervisor required |

Severity by reason code (`SeverityForReason`; unknown codes are graded 2):

| Code | Text | Severity | Modern `reason_code` |
|---|---|---|---|
| R01 | INVALID ACCT | 3 | `INVALID_ACCOUNT_IDENTIFIER` |
| R02 | MISSING BIC | 2 | `MISSING_BENEFICIARY_BIC` |
| R03 | NAME MISMATCH | 3 | `BENEFICIARY_NAME_MISMATCH` |
| R04 | DUPLICATE | 3 | `DUPLICATE_REFERENCE` |
| R05 | LIMIT | 3 | `AMOUNT_LIMIT_EXCEEDED` |
| R06 | CUTOFF | 2 | `CUTOFF_MISSED` |
| R07 | SCREENING | 4 | `SCREENING_REVIEW` |
| R08 | NSF | 2 | `INSUFFICIENT_FUNDS` |
| R09 | STALE DATE | 1 | `STALE_VALUE_DATE` |
| R10 | PURPOSE | 2 | `MISSING_PURPOSE_CODE` |
| R11 | CCY/RAIL | 3 | `UNSUPPORTED_CURRENCY_RAIL` |

Both thresholds are inclusive (`>=`). The function never raises: an unknown
reason code routes with severity 2 and an unknown segment goes to `CORP-STD`.

Example - the hero exception `MGB-EXC-0231` (R03, 480,000 USD, institutional):
`INST-HV`, severity 3, supervisor required.

## Why it was retired

* It ran only on Windows desktops with the VB6 runtime and an ODBC link to the
  desk database; the rules could not be invoked from the server side, so the
  modern API had no way to assign a queue without re-implementing them.
* The thresholds and severity table were compiled into the executable
  (see the module header history: raising the institutional threshold in 2008
  required a desktop rollout).
* `Currency` arithmetic (fixed four decimals, 64-bit) and `Integer` severities
  do not map to the typed decimal and enum model of the new platform.

## How the Python reference and fixtures were derived

`services/api/app/integrations/legacy/exception_routing.py` is a direct
transcription of `RouteException`, `SeverityForReason` and `ReasonText`,
keeping the same evaluation order (screening first, then queue by
segment/amount, then the supervisor rule) and the same `Case Else` behavior.

`legacy/reference-tests/fixtures/exception_routing_cases.json` (26 cases) was
built by walking the `Select Case` branches and the two thresholds: each reason
code at least once, each queue, each severity, both sides of 250,000 and
100,000, the screening override on every segment, an unknown code, an unknown
segment and untrimmed/lower-case input. Expected values were derived by hand
from the VB6 source and then confirmed against the Python reference.

## Verification - and what cannot be verified here

**VB6 cannot be compiled or run on the build machines** (macOS/Linux CI, no
VB6 IDE or runtime), so unlike the COBOL program there is no execution-based
golden test. The parity gate for this component is therefore:

1. `legacy/reference-tests/test_exception_routing_golden.py` runs every fixture
   through the Python reference, for both the legacy `Rnn` code and the modern
   `reason_code` spelling;
2. the same test module **parses `modExceptionRouting.bas`** - the `Public
   Const` block, the `SeverityForReason` and `ReasonText` `Select Case` tables -
   and asserts they equal the Python module's constants and tables, so the
   source of record and the reference cannot drift apart silently;
3. `services/api/tests/unit/legacy/test_exception_routing.py` covers the rule
   edges directly.

If a Windows machine with VB6 (or the VB6 runtime plus a compiled `PRD32.exe`)
becomes available, `frmReviewQueue` can be used to spot-check the fixtures
manually; the form shows queue, severity and the supervisor flag for any input.
