# ADR 0002: Scenario clock and deterministic seed

* Status: Accepted
* Date: 2026-03-04
* Deciders: Payments Platform Engineering, Payments Operations

## Context

Payments operations software is about time: settlement cutoffs, exception
SLAs, "processed today", ages of open items. A demonstration, a training
session or an incident drill must show the same screen every time it is run,
with the same payments at the same ages and the same windows about to close.
Real wall-clock time makes that impossible: an exception that is "due in 1h 50m"
on Wednesday is overdue by Thursday, and a cutoff window that is open at 14:00
is closed at 17:00.

The seeded dataset has the same requirement. If generated rows differ between
runs, screenshots, test assertions, fixture files and incident evidence drift
apart.

## Decision

### Scenario clock

The application's notion of "now" is a setting, not the system clock.

* `settings.scenario_now` (environment `MF_SCENARIO_NOW`, default
  `2026-03-18T18:40:00Z`, a Wednesday) is the single source of the current
  instant.
* All business code obtains time from `app.core.clock.now()` /
  `app.core.clock.today()`. `datetime.now()` and `date.today()` are banned in
  business code (ruff `DTZ` rules are enabled; the clock module is the only
  sanctioned caller).
* Every datetime is timezone-aware. The database stores UTC ISO-8601 strings
  with offset. Settlement cutoffs are computed in the rail's business timezone
  using `zoneinfo.ZoneInfo` and the timezone *name* is stored next to the
  cutoff instant, so a reader can always reconstruct the local wall time.
* The web application reads `GET /api/v1/meta/scenario` and drives every
  countdown, age and "today" from `scenario_now`, never from the browser clock.
  The top bar shows the scenario time explicitly ("Scenario time 18:40 UTC -
  Wed 18 Mar 2026") so nobody mistakes it for real time.
* Audit events and payment events record the scenario time of the action; the
  real wall-clock time is not stored as business data.

### Deterministic seed

* The seed generator uses `random.Random(20260318)` for every random choice and
  never the module-level `random` functions. Re-running the seed produces
  byte-identical rows.
* Identifiers that would normally be random are derived: `uuid5` on stable
  keys (for example payment reference + event sequence), never `uuid4()`.
  Public references follow documented blocks per channel (`MGB-PAY-1000+`
  portal, `2000+` API, `5000+` file, `8000+` branch).
* The seed is idempotent: it records `seed_version` (`2026.03.1`),
  `scenario_now` and `payment_count` in a `seed_metadata` table and refuses to
  re-seed unless forced. `seed verify` re-derives the dataset invariants
  (exception/hold consistency, balanced journals, batch totals, contiguous
  event sequences, due-by after opened-at, minor-unit precision) and exits
  non-zero on any violation.
* Hand-authored anchors (the hero payment `MGB-PAY-1042`, the incident batch
  `SB-20260317-SEPA-02`, the pending approvals) are generated with explicit
  values, not drawn from the RNG, so narrative changes do not reshuffle the
  rest of the dataset.

## Consequences

* Tests can assert exact ages, countdowns and window states; `freezegun` is
  only needed for the clock module's own tests.
* Golden fixtures, screenshots and incident evidence remain valid for as long
  as the seed version is unchanged; changing the dataset is a versioned event.
* Operators must remember the application does not advance time by itself.
  Moving the scenario forward is a configuration change (`MF_SCENARIO_NOW`),
  which is the intended way to rehearse "what does the desk look like at 20:35
  after the WIRE cutoff".
* Code that needs real time for infrastructure reasons (log timestamps,
  request durations) uses it explicitly and labels it as such; it is never
  mixed into domain fields.
* Because cutoffs are computed from a configurable instant in the rail's
  business timezone, any calendar date can be rehearsed by changing
  `MF_SCENARIO_NOW` rather than by waiting for it.
