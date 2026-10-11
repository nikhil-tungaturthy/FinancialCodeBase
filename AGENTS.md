# Agent guide — Meridian Flow

Synthetic payments operations desk. Do not add calls to real banks, schemes, or customer data. Do not implement MGB-142, MGB-143, or MGB-318 on `main` unless you were asked to build that ticket. MGB-407 must not land on `main`.

## Commands

```bash
make setup
make seed
make dev
make test
make lint
make typecheck
make demo-reset FORCE=1
```

API: `uv run uvicorn app.main:app --app-dir services/api --port 8000`
Web: `npm run dev -w apps/web` (http://localhost:5173, proxies `/api` to port 8000)

Scenario clock: `MF_SCENARIO_NOW` (default `2026-03-18T18:40:00Z`). Business code reads `app.core.clock.now()`, never `datetime.now()`.

## Layout

| Path | Responsibility |
| --- | --- |
| `apps/web/src/features` | One folder per desk page. API clients live next to the page. |
| `services/api/app/domain` | Pure rules: fees, validation, cutoff, reconciliation match, exception classification |
| `services/api/app/services` | Load and change payments, exceptions, approvals, batches |
| `services/api/app/seed` | Deterministic scenario. Anchors are explicit; the rest uses `Random(20260318)`. |
| `services/batch` | Daily reconciliation and the idempotent ledger poster |
| `legacy/` | COBOL `FEECALC01` and VB6 `modExceptionRouting`, plus golden tests |

`WIRE_USD` and `SWIFT_INTL` fees come from `compute_fee` → `calculate_wire_fee`. Other rails use `MODERN_TARIFF`. Exception queue and severity come from `classify_exception` → `route_exception`.

## Invariants

- Money is `decimal.Decimal`. Do not use `float`.
- Datetimes are timezone-aware. Cutoffs are computed in the rail's IANA timezone.
- Payment status changes go through `services.workflow.transition`, which enforces `ALLOWED_TRANSITIONS`.
- A held payment has an open exception. Journals balance (debits equal credits) per `journal_ref`.
- Reconciliation matches a settlement entry only when it has exactly one principal credit of the same amount. It does not classify missing vs duplicate vs amount mismatch — that is MGB-318.
- Replaying the same settlement inputs returns the existing reconciliation row (`input_hash`).

## Safe changes

- Add tests next to the behaviour you change. `make test-api` runs pytest for the API, batch jobs, and legacy references.
- Do not put presenter answer keys, oracles, or demo-kit files in this repository.
- Demo identity is `X-Demo-User`. Do not replace it with a fake production auth stack.
- Cloud agents: `make setup && make seed && make test` is enough. No secrets are required for the core app.

## Tickets

Read `docs/product/tickets/` before planning MGB-142 or MGB-318. The policy document `services/api/app/domain/policies/exception_reasons.json` is the source for exception guidance; do not hard-code a second copy in React.
