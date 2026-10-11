# Legacy modernization: FEECALC01 and modExceptionRouting

Meridian Flow replaces two pieces of retired technology whose *behavior* must
survive the replacement exactly: the mainframe fee batch `FEECALC01` (COBOL)
and the Payments Review Desk routing module `modExceptionRouting` (Visual
Basic 6). This document explains what each piece did, how the modern services
depend on them, the reference tables an engineer needs when reading a fee or a
queue assignment, and how parity is tested. The decision record is
[ADR 0003](adr/0003-legacy-fee-and-routing-modernization.md).

## 1. What lives where

| Component | Source of record | Python reference | Consumed by | Parity tests |
|---|---|---|---|---|
| Wire/SWIFT fee tariff | `legacy/cobol/FEECALC01.cbl` + `copybooks/FEESCHED.cpy` | `app/integrations/legacy/feecalc.py` (`calculate_wire_fee`) | `app/domain/fees/service.py` for rails `WIRE_USD`, `SWIFT_INTL` (`FeeQuote.source = LEGACY_FEECALC01`) | `legacy/reference-tests/test_feecalc_golden.py` (fixtures + compiled COBOL), `services/api/tests/unit/legacy/test_feecalc.py` |
| Exception routing | `legacy/vb6/modExceptionRouting.bas` (+ `frmReviewQueue.frm`) | `app/integrations/legacy/exception_routing.py` (`route_exception`) | `app/domain/exceptions/classification.py` for `queue` and initial severity; `legacy_code` in `exception_reasons.json` | `legacy/reference-tests/test_exception_routing_golden.py` (fixtures + static parse of the `.bas`), `services/api/tests/unit/legacy/test_exception_routing.py` |
| Golden fixtures | `legacy/reference-tests/fixtures/*.json` | - | tests, `legacy/cobol/run_fixtures.sh` | - |

The Python reference modules are deliberately standard-library-only and free of
ORM, framework or settings imports. They can be imported from the API, the
batch service, scripts and tests without side effects.

## 2. FEECALC01 - the fee tariff

### Purpose

`FEECALC01` was the nightly job that priced every outbound wire and SWIFT
payment from a fixed-width extract. Fee income, customer statements and the
general ledger fee legs all depended on its output, so the modern service must
produce the same number to the cent for the same input.

### Reference behavior

Inputs: amount (`PIC 9(13)V99`, so `0.00` to `9,999,999,999,999.99` with two
decimals), segment code `I`/`C`/`R`, rail code `WIRE`/`SWIFT`.

| Step (COBOL paragraph) | Rule |
|---|---|
| `2100-SELECT-BAND` | First band whose **inclusive** upper bound is >= amount |
| `2200-COMPUTE-BANDED-FEE` | `bps = ROUND_HALF_UP(amount x rate, 2)`; `banded = base + bps` |
| `2300-APPLY-CAP` | `capped = min(banded, 250.00)`; flag set only when `banded > 250.00` |
| `2400-APPLY-SEGMENT` | `segmented = ROUND_HALF_UP(capped x multiplier, 2)` |
| `2500-APPLY-RAIL-SURCHARGE` | `fee = segmented + 12.00` for SWIFT, `+ 0.00` for WIRE |

Band table (`FEESCHED.cpy`, version `2026.03.01`):

| Band | Amount | Base fee | Rate | Example |
|---|---|---|---|---|
| 1 | <= 10,000.00 | 15.00 | 0 bps | 5,000.00 / C -> 15.00 |
| 2 | 10,000.01 - 100,000.00 | 25.00 | 1.0 bps (0.000100) | 50,000.00 / C -> 30.00 |
| 3 | 100,000.01 - 1,000,000.00 | 35.00 | 0.5 bps (0.000050) | 480,000.00 / I -> 47.20 |
| 4 | > 1,000,000.00 | 50.00 | 0.25 bps (0.000025) | 2,500,000.00 / I / SWIFT -> 102.00 |

Segment multipliers: institutional `0.80`, corporate `1.00`, retail `1.10`.
Cap `250.00` on the banded fee only. SWIFT surcharge `12.00` after the
multiplier, never capped.

Properties worth knowing when reading fees:

* **The fee drops when crossing into band 4.** 1,000,000.00 prices at 85.00
  (35 + 50.00); 1,000,000.01 prices at 75.00 (50 + 25.00). This is the original
  tariff and is preserved on purpose.
* **Rounding is half-up at two points**, not bankers' rounding. 10,050.00
  corporate is 26.01 (bps 1.005 -> 1.01); 11,500.00 retail is 28.77
  (26.15 x 1.10 = 28.765 -> 28.77). A `float` or `ROUND_HALF_EVEN`
  re-implementation produces different cents on roughly one in a hundred
  payments.
* **The cap is strict.** 8,000,000.00 corporate gives a banded fee of exactly
  250.00 and is not flagged as capped; 8,000,200.00 is the first capped amount.
  A retail payment above the cap pays 275.00 (250 x 1.10) and a SWIFT payment
  pays the surcharge on top (262.00 corporate), because the multiplier and the
  surcharge are applied after the cap.
* **Segment mapping.** The tariff only knows `I`/`C`/`R`. The reference accepts
  the modern `CustomerSegment` names and maps `INTERNAL` (the bank's own
  treasury) to the corporate schedule, which is how the mainframe priced
  internal movements that went out over a wire rail. `INTERNAL_BOOK` transfers
  never reach `FEECALC01`; they are priced by the modern fee schedule.
* **Rails.** `WIRE_USD -> WIRE`, `SWIFT_INTL -> SWIFT`. Any other rail raises
  `FeeCalcInputError` (status `02`); the fee service must not route ACH, SEPA,
  CHAPS or internal-book payments here.

### How the modern fee service uses it

`app/domain/fees/service.py: compute_fee(rail, currency, segment, amount)`:

```
if rail in {WIRE_USD, SWIFT_INTL}:
    result = calculate_wire_fee(amount, segment.value, rail.value)
    return FeeQuote(amount=result.fee, currency=currency,
                    source="LEGACY_FEECALC01", breakdown=result.as_breakdown())
else:
    ... fee_schedules rows (FLAT | FLAT_PLUS_BPS, min/max), source="MODERN"
```

`FeeCalcResult` exposes `fee`, `band`, `base_fee`, `bps_component`,
`banded_fee`, `capped`, `multiplier`, `surcharge` and `as_breakdown()` (all
amounts as two-decimal strings) so the payment detail and the Policies page can
show the composition of a legacy fee without re-deriving it. The hero payment
`MGB-PAY-1042` (USD 480,000.00, institutional, WIRE_USD) carries fee `47.20`
with source `LEGACY_FEECALC01` for exactly this reason.

The `fee_schedules` table has rows with `source = LEGACY_FEECALC01` for
`WIRE_USD`/`SWIFT_INTL` for display only; they are not used to price. The
`business_rules` rows for the tariff carry `legacy_origin = "COBOL FEECALC01"`.

## 3. modExceptionRouting - queue, severity, supervisor

### Purpose

When validation holds a payment, somebody has to look at it. The desk module
decided *who* (queue), *how urgently* (severity 1-4) and *with what authority*
(supervisor sign-off). The modern workbench keeps the same queues so that
operations staffing, SLA reporting and the audit trail remain comparable
before and after the migration.

### Reference behavior

`RouteException(reasonCode, amountUsd, segment)`, evaluated in this order:

| Order | Condition | Outcome |
|---|---|---|
| 1 | reason `R07` SCREENING | `FCR-SCREEN`, severity 4, supervisor required |
| 2 | segment `I` and amount >= 250,000 USD | `INST-HV` |
| 3 | segment `R` | `RETAIL-STD` |
| 4 | otherwise (`C`, institutional below threshold, unknown segment) | `CORP-STD` |
| 5 | severity >= 3 or amount >= 100,000 USD | supervisor required |

Severity and the legacy <-> modern code map:

| Legacy | Text | Sev | Modern `reason_code` | Policy default severity |
|---|---|---|---|---|
| R01 | INVALID ACCT | 3 | `INVALID_ACCOUNT_IDENTIFIER` | HIGH |
| R02 | MISSING BIC | 2 | `MISSING_BENEFICIARY_BIC` | MEDIUM |
| R03 | NAME MISMATCH | 3 | `BENEFICIARY_NAME_MISMATCH` | HIGH |
| R04 | DUPLICATE | 3 | `DUPLICATE_REFERENCE` | HIGH |
| R05 | LIMIT | 3 | `AMOUNT_LIMIT_EXCEEDED` | HIGH |
| R06 | CUTOFF | 2 | `CUTOFF_MISSED` | MEDIUM |
| R07 | SCREENING | 4 | `SCREENING_REVIEW` | CRITICAL |
| R08 | NSF | 2 | `INSUFFICIENT_FUNDS` | MEDIUM |
| R09 | STALE DATE | 1 | `STALE_VALUE_DATE` | LOW |
| R10 | PURPOSE | 2 | `MISSING_PURPOSE_CODE` | MEDIUM |
| R11 | CCY/RAIL | 3 | `UNSUPPORTED_CURRENCY_RAIL` | HIGH |

The numeric severities map 1:1 onto `ExceptionSeverity` (`SEVERITY_LABELS`),
and they agree with the `default_severity` values in
`app/domain/policies/exception_reasons.json`, whose `legacy_code` field holds
the `Rnn` code. Reasons that post-date the desk (for example `FX_QUOTE_EXPIRED`)
have no legacy code: `to_legacy_reason()` returns `None` and `route_exception()`
grades them severity 2 (the VB6 `Case Else`) and routes by segment.

### How the modern classification uses it

`app/domain/exceptions/classification.py` calls
`route_exception(reason_code, payment.usd_equivalent, customer.segment.value)`
when an exception is raised and copies `RoutingResult.queue` to
`payment_exceptions.queue` and `RoutingResult.severity_label` to the initial
`severity` (the reason policy may override severity; the queue is always the
desk's). `requires_supervisor` feeds the allowed-actions computation alongside
the approval policy. The hero exception `MGB-EXC-0231` sits in `INST-HV` with
severity HIGH because R03 at USD 480,000 institutional routes there.

## 4. Testing strategy

Three layers, from cheapest to most authoritative. All legacy tests carry the
`legacy` pytest marker (registered in the root `pyproject.toml`).

1. **Unit tests of the Python references** (`services/api/tests/unit/legacy/`):
   band edges, both half-up rounding points, the strict cap, cap-before-
   multiplier-before-surcharge ordering, the field maximum, input
   normalization and the three rejection statuses; threshold inclusivity,
   screening override, `Case Else` behavior and the code maps for routing.
   Floats are rejected with `TypeError` in both modules.
2. **Golden fixtures** (`legacy/reference-tests/fixtures/`): 30 fee cases and
   26 routing cases with hand-derived expectations. The golden tests also
   assert the fixture files keep their required coverage (every band edge, the
   hero payment, every segment and rail, cap hits including cap + surcharge;
   every reason code, every queue, every severity, an unknown code), so the
   fixtures cannot be thinned out without a failing test.
3. **Execution of the legacy program** (`test_feecalc_golden.py`): when `cobc`
   is on `PATH` (or `$COBC` is set) the COBOL is compiled into a pytest
   temporary directory and run on the fixture input and on a seeded sweep of
   1,440 records; fee, band and cap flag must match the fixtures and the
   Python reference for every record, and malformed records must come back
   with the documented status codes and `RETURN-CODE 4`. Without GnuCOBOL the
   tests skip with `GnuCOBOL (cobc) not installed; COBOL not executed -
   Python reference + fixtures only`. On the build machine (GnuCOBOL 3.2.0 via
   Homebrew) the COBOL path runs and passes; see `legacy/cobol/README.md` for
   the recorded output.

   VB6 has no equivalent: it cannot be compiled on macOS or Linux. The routing
   golden test instead parses the `.bas` source (constants, severity table,
   reason text table) and asserts equality with the Python module, so the
   source of record and the reference cannot diverge silently.

Run everything with:

```bash
uv run pytest legacy/reference-tests services/api/tests/unit/legacy -q
bash legacy/cobol/build.sh && bash legacy/cobol/run_fixtures.sh
```

CI should treat a skip of the COBOL execution tests as a warning on developer
machines and as a failure on the pipeline image that has GnuCOBOL installed.

## 5. Migration constraints

These are the rules every change to the legacy-governed behavior must respect.
The reasoning is in ADR 0003.

* **Money is `Decimal`, rounding is `ROUND_HALF_UP` to the currency's minor
  units.** The COBOL's `ROUNDED` is nearest-away-from-zero; for non-negative
  amounts that is half-up. Never introduce `float` or `ROUND_HALF_EVEN` on
  this path.
* **Band bounds are inclusive upper bounds** tested in ascending order. An
  implementation using `<` instead of `<=` differs at exactly the four edge
  amounts the fixtures pin.
* **Order of operations is band -> round -> cap -> multiply -> round ->
  surcharge.** Re-ordering (for example capping after the multiplier) changes
  retail fees above 8,000,200.00 and every SWIFT fee at the cap.
* **Tariff changes go through `FEESCHED.cpy` first**, then the Python
  constants, then the fixtures, in one change, with `FEESCHED_VERSION` bumped.
  The golden tests fail if any of the three disagree.
* **Field limits are part of the contract.** Amounts above `9,999,999,999,999.99`
  or with sub-cent precision are rejected (status `03`), as the batch rejected
  them. Fees fit `9(7)V99`.
* **Queue codes are keys, not labels.** `INST-HV` etc. appear in
  `payment_exceptions.queue`, in SLA reporting and in the audit trail; renaming
  them is a data migration, not a string change.
* **Both routing thresholds are inclusive (`>=`)** and screening is evaluated
  before the segment rules.
* **Unknown inputs behave as the legacy did:** the tariff rejects them, the
  router degrades them (severity 2, `CORP-STD`). Callers must not "fix" either
  side without a policy decision and a fixture update.
* **Cutoff logic is not legacy-governed.** Settlement windows are computed in
  the rail's business timezone with `zoneinfo` and the timezone name is stored
  next to the instant (ADR 0002); the legacy batch's single-site-clock
  convention is not carried over.
