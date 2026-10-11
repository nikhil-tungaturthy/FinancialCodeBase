# Architecture

Meridian Flow is a single-process API plus a Vite web app. SQLite holds the scenario. Nothing in the request path calls an external system.

```
Browser
  └─ apps/web  (React, TanStack Query)
        └─ /api/v1
              └─ services/api
                    ├─ routers        HTTP
                    ├─ services       reads and state changes
                    ├─ domain         fees, validation, cutoffs, matching, classification
                    ├─ models         SQLAlchemy
                    └─ seed           deterministic scenario
              └─ services/batch       reconciliation and ledger posting
```

Payment status changes go through `services.workflow.transition`. That function is the only place a live payment moves, and it consults `domain.payments.lifecycle`.

Fees for `WIRE_USD` and `SWIFT_INTL` are computed by the Python reference of COBOL `FEECALC01`. Other rails use the modern tariff in `domain.fees.service`. Exception queue and initial severity come from the Python reference of the VB6 review desk.

Reconciliation compares settlement entries with principal-credit ledger rows. A row matches only when there is exactly one credit of the same amount. Classifying *why* a row failed to match is intentionally not implemented (MGB-318).

The scenario clock is `MF_SCENARIO_NOW`. Countdowns, ages and "today" use it. Log timestamps use the wall clock and are labelled as such.
