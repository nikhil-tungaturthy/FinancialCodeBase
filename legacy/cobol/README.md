# FEECALC01 - outbound wire / SWIFT fee calculation (COBOL)

`FEECALC01` is the nightly mainframe batch that priced outbound `WIRE` and
`SWIFT` payments at Meridian Global Bank. It is preserved here, unchanged in
logic, because the modern platform must charge exactly the fee this program
charged. `services/api/app/integrations/legacy/feecalc.py` is a line-for-line
Python reference of it, and `legacy/reference-tests/test_feecalc_golden.py`
compiles and executes this program (when GnuCOBOL is installed) to prove the two
agree.

| File | Purpose |
|---|---|
| `FEECALC01.cbl` | The program: read `FEEIN`, price each record, write `FEEOUT`. Fixed-format source (columns 8-72). |
| `copybooks/FEESCHED.cpy` | The tariff: band table, segment multipliers, cap, SWIFT surcharge, code values. The program contains no tariff literals. |
| `build.sh` | Compiles with `cobc -x` into `build/feecalc01` (the `build/` directory is gitignored). |
| `run_fixtures.sh` | Encodes the golden fixtures into a `FEEIN` file, runs the binary, prints `FEEOUT`, and compares every record against `expected_fee`. |

## Record layouts

Both files are `ORGANIZATION LINE SEQUENTIAL` (one record per line, no record
length prefix). All numeric fields are unsigned display digits with an implied
decimal point.

### FEEIN (21 bytes)

| Columns | Field | Picture | Notes |
|---|---|---|---|
| 1-15 | `AMOUNT` | `9(13)V99` | Plain digits, two implied decimals. `480000.00` is `000000048000000`. |
| 16 | `SEGMENT-CODE` | `X` | `I` institutional, `C` corporate, `R` retail. |
| 17-21 | `RAIL-CODE` | `X(5)` | `WIRE ` (space padded) or `SWIFT`. `WIRE_` is accepted as an alias because one upstream extract pads with underscore. |

Blank records are skipped (counted as `SKIPPED`, no output line).

### FEEOUT (34 bytes)

| Columns | Field | Picture | Notes |
|---|---|---|---|
| 1-21 | input record echo | `X(21)` | Byte-identical copy of the FEEIN record. |
| 22-30 | `FEE` | `9(7)V99` | `47.20` is `000004720`. Zero when the record is rejected. |
| 31 | `BAND` | `9` | `1`-`4`; `0` when rejected. |
| 32 | `CAP-FLAG` | `X` | `Y` when the banded fee exceeded the cap, else `N`. |
| 33-34 | `STATUS` | `XX` | `00` priced; `01` bad segment; `02` bad rail; `03` amount not numeric. |

Validation runs in the order amount (`03`), segment (`01`), rail (`02`); the
first failure is reported. Rejected records still produce an output line so the
downstream job can reconcile counts.

### Return codes

| RC | Meaning |
|---|---|
| 0 | Every non-blank record priced. |
| 4 | One or more records rejected (written with a non-zero `STATUS`). |
| 12 | File open or write failure; message on `SYSOUT`. |

## Calculation

Values come from `FEESCHED.cpy`; the paragraph numbers are the ones in the source.

```
2100-SELECT-BAND          first band (ascending) whose INCLUSIVE upper bound >= amount
                            band 1  amount <=        10,000.00   base 15.00   rate 0.000000
                            band 2  amount <=       100,000.00   base 25.00   rate 0.000100 (1.0 bps)
                            band 3  amount <=     1,000,000.00   base 35.00   rate 0.000050 (0.5 bps)
                            band 4  amount >      1,000,000.00   base 50.00   rate 0.000025 (0.25 bps)
2200-COMPUTE-BANDED-FEE   bps = ROUNDED(amount * rate) to 2 dp;  banded = base + bps
2300-APPLY-CAP            capped = MIN(banded, 250.00)   (strict >, so 250.00 exactly is not a cap hit)
2400-APPLY-SEGMENT        segmented = ROUNDED(capped * multiplier)   I 0.80 / C 1.00 / R 1.10
2500-APPLY-RAIL-SURCHARGE fee = segmented + 12.00 when SWIFT, else + 0.00   (never capped)
```

Worked example, the hero payment `MGB-PAY-1042` (480,000.00 / I / WIRE):
band 3, bps `480,000.00 x 0.000050 = 24.00`, banded `35.00 + 24.00 = 59.00`,
no cap, `59.00 x 0.80 = 47.20`, no surcharge: **47.20**.

### Rounding semantics

Every `COMPUTE ... ROUNDED` in the program relies on the compiler's default
rounding mode. For GnuCOBOL that default is `NEAREST-AWAY-FROM-ZERO`, which for
the non-negative values this program handles is identical to "round half up"
(`decimal.ROUND_HALF_UP` in Python). This was verified empirically on the build
machine with a probe program rather than assumed:

```
10050.00*0.0001 ROUNDED  =       1.01      (half-up; bankers' rounding would give 1.00)
26.15*1.10 ROUNDED       =      28.77      (half-up; bankers' rounding would give 28.76)
8000200.00*0.000025 RND  =     200.01
8000199.99*0.000025 RND  =     200.00
26.15*1.10 NEAREST-EVEN  =      28.76      (explicit mode, for comparison)
26.15*1.10 AWAY-FROM-ZERO=      28.77      (explicit mode, matches the default)
```

Intermediate products are exact (GnuCOBOL computes `COMPUTE` expressions with
arbitrary-precision decimals; the rate has six decimals, the amount two), so the
two `ROUNDED` statements are the only rounding points.

The pre-cap work fields are `PIC 9(10)V99`, wider than the output fee: the
maximum amount `9,999,999,999,999.99` in band 4 (0.25 bps) gives a
`250,000,000.00` bps component (249,999,999.99999975 rounded) before the cap
brings the fee to `250.00`. A `9(7)V99` work field raises a size error there
(observed with a probe program during development; the field widths in the
source are the fix).

## Build and run

Requires GnuCOBOL 3.x. On this machine it is the Homebrew package at
`/opt/homebrew/bin/cobc`.

```bash
bash legacy/cobol/build.sh                       # -> legacy/cobol/build/feecalc01
DD_FEEIN=/path/to/FEEIN DD_FEEOUT=/path/to/FEEOUT legacy/cobol/build/feecalc01
bash legacy/cobol/run_fixtures.sh                # fixtures -> FEEIN -> binary -> compare
```

Files are assigned by external name (`ASSIGN TO "FEEIN"`), so GnuCOBOL resolves
the path from the environment variables `DD_FEEIN` / `DD_FEEOUT` (or `FEEIN` /
`FEEOUT`), falling back to files of those names in the working directory. This
mirrors the JCL `DD` statements the job originally ran with.

`run_fixtures.sh` uses the FEEIN encoder and FEEOUT parser from
`app.integrations.legacy.feecalc` (through `uv run`) so that the record layout
is defined in one place.

## Actual result on the build machine

Recorded from a real run, not transcribed from expectations.

Compiler:

```
$ /opt/homebrew/bin/cobc --version
cobc (GnuCOBOL) 3.2.0
Copyright (C) 2023 Free Software Foundation, Inc.
...
Built     Jul 28 2023 18:42:18
build environment        : aarch64-apple-darwin25.4.0
```

Compile:

```
$ bash legacy/cobol/build.sh
build.sh: cobc (GnuCOBOL) 3.2.0
build.sh: compiling FEECALC01.cbl -> .../legacy/cobol/build/feecalc01
.../legacy/cobol/FEECALC01.cbl:3: warning: AUTHOR is obsolete in GnuCOBOL [-Wobsolete]
build.sh: ok
```

The single warning is the `AUTHOR` paragraph, which is standard in programs of
this vintage and is kept deliberately; `-Wall` is on so anything new will show.

Fixture run (30 records):

```
$ bash legacy/cobol/run_fixtures.sh
run_fixtures.sh: 30 FEEIN records written
run_fixtures.sh: running FEECALC01
FEECALC01: START, FEE SCHEDULE 2026.03.01
FEECALC01: END, READ=0000030 WRITTEN=0000030 ERRORS=0000000 SKIPPED=0000000
run_fixtures.sh: FEECALC01 RETURN-CODE=0

---- FEEOUT ----
000000000000000CWIRE 0000015001N00
000000001000000CWIRE 0000015001N00
000000001000001CWIRE 0000026002N00
000000001005000CWIRE 0000026012N00
000000001150000RWIRE 0000028772N00
000000048000000IWIRE 0000047203N00      <- hero: 47.20, band 3, not capped
000000100000000CWIRE 0000085003N00
000000100000001CWIRE 0000075004N00
000000800020000CWIRE 0000250004Y00      <- first cap hit
000001000000000RWIRE 0000275004Y00      <- cap x 1.10
000002500000000CSWIFT0000262004Y00      <- cap + surcharge
999999999999999RSWIFT0000287004Y00      <- field maximum
(remaining records omitted here; the full table prints at run time)

run_fixtures.sh: 30/30 records match the golden fixtures
```

Rejected-record behavior, from a hand-built input (also asserted by the golden
test `test_cobol_rejects_malformed_records_with_status_codes`):

```
000000048000000XWIRE 0000000000N01      bad segment
000000048000000IACH  0000000000N02      bad rail
00000004800000AIWIRE 0000000000N03      amount not numeric
000000048000000IWIRE_0000047203N00      'WIRE_' alias priced normally
FEECALC01: END, READ=0000011 WRITTEN=0000010 ERRORS=0000003 SKIPPED=0000001   (RC 4)
```

The pytest golden suite additionally runs a seeded sweep of 240 amounts x 3
segments x 2 rails (1,440 records) through the binary and the Python reference
and requires identical fee, band and cap flag for every record.

## Differences from the original mainframe environment

* The original ran under JCL with fixed-block datasets; this copy uses
  `LINE SEQUENTIAL` files so it can be driven from a shell. Field positions are
  unchanged.
* The original compiler's default `ROUNDED` mode was also nearest-away-from-zero
  (the pre-2002 standard only had that behavior), so results are identical. If
  this source is ever compiled with a different compiler, re-run the golden
  suite before trusting it.
* `RETURN-CODE` values follow mainframe convention (0 / 4 / 12).
