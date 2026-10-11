# Meridian Flow

Global Payments & Exception Operations for the fictional Meridian Global Bank.

Meridian Flow is an internal operations desk. Analysts use it to see where a payment sits, why it was held, whether it will make the next settlement window, and how the ledger and reconciliation records line up. Every customer, amount, and account in the database is synthetic. The application does not call a real bank, payment scheme, or core banking system.

## Architecture

```
apps/web          React, TypeScript, Vite, Tailwind
services/api      FastAPI, SQLAlchemy, SQLite
services/batch    settlement posting and daily reconciliation
legacy/           COBOL fee program and a VB6 review-desk module, with Python references
```

The web app talks only to `/api/v1`. Money is `Decimal` end to end and is serialised as a string. "Now" is a fixed scenario clock (`2026-03-18T18:40:00Z`), not the wall clock, so the same payment is the same age every time you open the desk.

## Quick start

```bash
make setup
make seed
make dev
```

- Desk: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health and http://localhost:8000/ready

`make ready` waits until both processes answer.

Demo identity is the `X-Demo-User` header (the desk sends it for you). The default persona is `priya.raman`, a payments analyst. Other personas are in the identity switcher. This is not production authentication.

## Tests

```bash
make test          # pytest and vitest
make test-e2e      # Playwright; API and web must already be running
make lint
make typecheck
```

## Reset

`make demo-reset` deletes `data/meridian_flow.db` (and its SQLite sidecars) after a confirmation, then reseeds. `make demo-reset FORCE=1` skips the prompt. It does not touch source files.

## Seeded story

The seed is deterministic (`random.Random(20260318)`, version `2026.03.1`) and produces about 485 payments.

- **MGB-PAY-1042** — Helios Capital Partners, USD 480,000.00 wire, fee 47.20 from the legacy `FEECALC01` tariff. Status `HELD`. Exception **MGB-EXC-0231** (`BENEFICIARY_NAME_MISMATCH`, queue `INST-HV`). The instruction says "Aurelia Market GmbH"; the register says "Aurelia Markets GmbH". At the scenario clock the USD wire window closes in 110 minutes.
- **SB-20260317-SEPA-02** — settled SEPA batch with a +18,450.00 EUR variance. Reconciliation `RR-000061` lists ledger credits `LE-002448` and `LE-002452` as unmatched. Incident **INC-2026-0318-004** points at the evidence under `shared/fixtures/incidents/`.

## What the baseline deliberately does not include

These are the live demo tasks. The surrounding data and APIs exist; the features do not.

| Ticket | Baseline gap |
| --- | --- |
| MGB-142 | No "Resolution Guidance" section on the exception workbench |
| MGB-143 | No visual refinement of that section |
| MGB-318 | Reconciliation shows variance and unmatched refs, not a classified investigation |
| MGB-407 | Lives only on `demo/mgb-407-cutoff-regression`, never on this branch |
| MGB-502 | Incident evidence and `make incident-emit` are here; a Cursor Automation is not installed |

Issue text is in `docs/product/tickets/`. Operating detail is in `docs/operations/local-development.md`.
