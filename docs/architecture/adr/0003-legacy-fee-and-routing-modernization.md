# ADR 0003: Modernizing the legacy fee tariff (COBOL) and exception routing (VB6)

* Status: Accepted
* Date: 2026-03-09
* Deciders: Payments Platform Engineering, Payments Operations, Finance (fee income)
* Related: ADR 0001 (monorepo), ADR 0002 (scenario clock),
  `docs/architecture/legacy-modernization.md`, `legacy/cobol/README.md`,
  `legacy/vb6/README.md`

## Context

Two retired components still define behavior that customers, finance and the
regulator can observe:

* **`FEECALC01`** (COBOL, nightly mainframe batch) priced every outbound WIRE
  and SWIFT payment. Its output fed fee income, customer statements and the
  general ledger fee legs. Tariff in copybook `FEESCHED`.
* **`modExceptionRouting`** (Visual Basic 6, Payments Review Desk client)
  decided the review queue, the initial severity and whether a supervisor had
  to sign off on every held payment. Its queue codes are the keys used in
  staffing, SLA reporting and the audit trail.

Neither can be run in the new environment (no mainframe; VB6 does not compile
on the CI platforms), yet the new platform must behave identically for the
same inputs on day one. A fee that differs by one cent is a customer-facing
billing error; an exception routed to a different queue breaks operational
reporting continuity and the four-eyes control.

## Existing behavior (what must be preserved)

**Fee tariff** (`FEECALC01`, paragraphs 2100-2500):

1. band by inclusive upper bound: <= 10,000.00 (15.00, 0 bps);
   <= 100,000.00 (25.00, 1.0 bps); <= 1,000,000.00 (35.00, 0.5 bps);
   above (50.00, 0.25 bps);
2. `banded = base + ROUNDED(amount x rate)` to 2 dp;
3. cap the banded fee at 250.00 (strict greater-than);
4. `ROUNDED(capped x multiplier)` with I 0.80 / C 1.00 / R 1.10;
5. add 12.00 for SWIFT (never capped).

`ROUNDED` is nearest-away-from-zero, which for the non-negative amounts in
scope is round-half-up. Inputs outside `PIC 9(13)V99`, unknown segments and
unknown rails are rejected with status codes, not priced.

**Routing** (`RouteException`): screening (`R07`) always to `FCR-SCREEN` at
severity 4 with supervisor; institutional with amount >= 250,000 USD to
`INST-HV`; retail to `RETAIL-STD`; everything else to `CORP-STD`; severity
from a per-code table (R01 3, R02 2, R03 3, R04 3, R05 3, R06 2, R07 4, R08 2,
R09 1, R10 2, R11 3; unknown 2); supervisor when severity >= 3 or amount
>= 100,000 USD. Thresholds are inclusive. Unknown inputs are degraded, never
rejected.

## Target behavior

* The platform owns both rules as **pure Python reference modules**
  (`app/integrations/legacy/feecalc.py`, `app/integrations/legacy/exception_routing.py`)
  with `Decimal` arithmetic and `ROUND_HALF_UP`, no framework or ORM imports,
  and typed result objects that expose the full breakdown (`FeeCalcResult`,
  `RoutingResult`).
* `domain/fees/service.py` delegates `WIRE_USD` and `SWIFT_INTL` to
  `calculate_wire_fee` and labels the quote `source = LEGACY_FEECALC01`; all
  other rails use the modern `fee_schedules` table (`source = MODERN`).
* `domain/exceptions/classification.py` takes `queue` and initial severity from
  `route_exception`; the exception reason policy carries the `legacy_code` so
  the two code systems stay linked.
* The legacy sources stay in the repository (`legacy/cobol`, `legacy/vb6`) as
  the **source of record**, readable and - for COBOL - compilable, so any
  question about "what did the old system do" is answered by running it, not
  by remembering.
* The modern tables (`fee_schedules` rows with `source = LEGACY_FEECALC01`,
  `business_rules` with `legacy_origin`) describe the tariff for display and
  policy pages but do not price; pricing is the reference module until a
  deliberate tariff change retires it.

## Validation requirements

The migration is accepted only while all of the following hold in CI:

1. **Golden fixtures.** `legacy/reference-tests/fixtures/feecalc_cases.json`
   (>= 24 cases; every band edge on both sides, each segment, SWIFT, cap hits
   including cap + surcharge, the hero payment 480,000.00 / I / WIRE -> 47.20)
   and `exception_routing_cases.json` (>= 20 cases; every reason code, every
   queue, every severity, both thresholds on both sides, unknown code and
   segment, untrimmed input). Expectations are derived by hand from the legacy
   sources, not generated from the Python code.
2. **Golden-master parity gate.** `test_feecalc_golden.py` compiles
   `FEECALC01.cbl` with GnuCOBOL and executes it on the fixture input and on a
   seeded sweep of 1,440 records; fee, band and cap flag must match the
   fixtures and the Python reference for every record, and rejected records
   must return the documented status codes. The pipeline image has GnuCOBOL
   3.2 installed; a skip there is treated as a failure. On machines without
   `cobc` the test skips with an explicit message and the Python-vs-fixture
   layer still runs.
3. **Static parity for VB6.** Because VB6 cannot execute, the routing golden
   test parses the `.bas` constants, severity table and reason text table and
   asserts equality with the Python module. A change to either side without
   the other fails the build.
4. **Unit coverage** of the rounding ties, the strict cap, operation order,
   field limits, threshold inclusivity, screening precedence and type
   discipline (floats raise `TypeError`).
5. **Dataset anchor.** The seeded hero payment `MGB-PAY-1042` (USD 480,000.00,
   institutional, WIRE_USD) carries fee 47.20 with source `LEGACY_FEECALC01`,
   and its exception `MGB-EXC-0231` sits in `INST-HV`. Both values are fixed
   in the dataset specification, so a parity regression on either path is
   visible in the seeded data as well as in the golden tests.
6. **Change protocol.** A tariff or routing change updates the legacy source,
   the Python reference and the fixtures in one reviewed change with the
   schedule version bumped; the gate above makes partial updates impossible to
   merge.

## Migration risks

| Risk | Where it bites | Mitigation |
|---|---|---|
| **Rounding mode** - `float`, `round()` (bankers') or `ROUND_HALF_EVEN` differ from the COBOL `ROUNDED` on ties such as 10,050.00 (1.005) and 11,500.00 retail (28.765). | roughly 1 in 100 fees off by one cent | `Decimal` + `ROUND_HALF_UP` only; tie cases pinned in fixtures; COBOL executed in CI |
| **Band edges** - `<` versus `<=`, or bands expressed as lower bounds with floating comparisons. | exactly the amounts 10,000.00 / 100,000.00 / 1,000,000.00 and one cent above | inclusive upper bounds in one table; all six edge amounts are fixtures |
| **Operation order** - capping after the multiplier, or applying the surcharge before the cap. | retail above 8,000,200.00 (275.00 vs 250.00), every SWIFT fee at the cap (262.00 vs 250.00) | order documented per paragraph; fixtures FC-26..FC-29 |
| **Data types** - COBOL `9(13)V99` unsigned fixed point, VB6 `Currency` (64-bit, 4 decimals) and `Integer` severities versus arbitrary `Decimal` and Python ints. Overflow, sub-cent input, negative amounts and `NULL` have no legacy meaning. | silent acceptance of inputs the legacy would have rejected or truncated | reference modules validate `0 <= amount <= 9,999,999,999,999.99` with at most two decimals and raise with the legacy status code; routing refuses floats; pre-cap work fields are wide enough for the field maximum (a `9(7)V99` work field overflows there) |
| **Band-crossing fee drop** - the fee falls from 85.00 to 75.00 when crossing into band 4; a "monotonic" sanity check or a well-meaning fix would change the tariff. | large payments | documented as intended; fixtures FC-19/FC-20 |
| **Unknown inputs** - the batch rejects, the desk degrades (severity 2, `CORP-STD`). Harmonizing either way changes behavior. | new reason codes such as `FX_QUOTE_EXPIRED`, the `INTERNAL` segment | both behaviors reproduced and tested; `INTERNAL` is mapped to the corporate schedule explicitly and documented |
| **Queue codes as keys** - renaming `INST-HV` etc. to friendlier labels breaks reporting joins and the audit history. | reporting, SLA dashboards | codes are constants shared by VB6 and Python; labels, if wanted, are a presentation concern |
| **Timezone handling for cutoffs** - the mainframe ran on one site clock and its cutoff times were wall-clock strings with no zone attached. Carrying that convention into the new platform would make every cutoff depend on where the process happens to run. | settlement window assignment, `CUTOFF_MISSED` exceptions, "closing soon" indicators | cutoffs are computed in the rail's business timezone with `zoneinfo` and the timezone name is stored with the instant (ADR 0002); the cutoff code is not part of the legacy reference and must not inherit its conventions |
| **Fixture decay** - someone deletes an inconvenient case. | silent loss of coverage | the golden tests assert the fixture files still contain every required edge |

## Why automated translation alone is insufficient

Transpiling the COBOL and VB6 to Python would produce code that compiles, and
it would still be wrong in the ways that matter:

* **Semantics live in the compiler, not the source.** `ROUNDED` means
  nearest-away-from-zero only because of the compiler's default; a translator
  that emits `round()` has translated the token and lost the behavior. The
  same is true of `PIC` truncation, `NUMERIC` class tests and VB6 `Currency`
  scaling.
* **Implicit contracts are not in the code.** That `WIRE_` is an accepted
  alias, that blank records are skipped, that `RETURN-CODE 4` means "some
  rejected", that queue codes are database keys - these are in job control,
  operating procedures and downstream consumers. They have to be discovered,
  written down (the READMEs) and tested.
* **The legacy code cannot be the oracle for itself.** A translation is only
  verifiable against executions of the original. For COBOL we can run it; for
  VB6 we cannot, so parity rests on hand-derived fixtures plus a structural
  comparison with the source. A translator gives neither.
* **Modernization changes the shape, not just the language.** The platform
  needs a typed result with a breakdown, explicit errors instead of status
  bytes, enum-friendly inputs and no I/O; a transliterated batch loop with
  global working storage would have to be wrapped and then re-tested anyway.
* **The decision of what to keep is a business decision.** The fee drop at
  the band-4 boundary and the degraded routing of unknown codes are preserved
  because Finance and Operations chose to; a tool cannot make that call, and a
  reviewer reading transpiled code cannot see that the call was made.

Automated translation was therefore used only as a reading aid. The
deliverables are the hand-written reference modules, the executable legacy
sources, the fixtures and the parity gate.

## Consequences

* Fee and routing behavior is reproducible, reviewable and covered by a gate
  that runs the original COBOL on every CI run.
* The team carries a small amount of COBOL and VB6 in the repository and a
  GnuCOBOL dependency in the CI image. This is a deliberate cost; it buys the
  ability to answer "what did the old system do" by execution.
* Future tariff changes are explicit three-part changes (legacy source,
  reference, fixtures). When the business decides to retire the legacy tariff
  for a new one, the reference module is replaced by a modern fee schedule
  entry and `source` changes from `LEGACY_FEECALC01` to `MODERN`; the golden
  tests for the old tariff are then archived with the ADR that supersedes this
  one.
* Cutoff logic remains modern-only; this ADR records that it is computed in
  the rail's business timezone (ADR 0002) and is not derived from the legacy
  batch's conventions.
