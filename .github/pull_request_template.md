## Summary

<!-- What changes and why, in two or three sentences. Link the design note or ADR if one exists. -->

## Linked ticket

Refs: MGB-

<!-- Tickets live in docs/product/tickets/. Use "Closes: MGB-xxx" when this PR completes the ticket. -->

## Change type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor (no behaviour change)
- [ ] Data / seed / policy change
- [ ] Docs / tooling / CI
- [ ] Legacy component (COBOL / VB6 / reference implementation)

## Financial-impact checklist

Answer every line; write "n/a" with a reason where it does not apply.

- [ ] **Decimal** — amounts stay `decimal.Decimal` in Python and strings on the wire and in the web app; no float arithmetic was introduced.
- [ ] **Rounding** — any rounding is explicit (`ROUND_HALF_UP` to the currency's minor units, JPY = 0) and covered by a test.
- [ ] **Transitions** — status changes go through the lifecycle module (`assert_transition`); invalid transitions still return 409.
- [ ] **Audit events** — every new or changed state-changing operation records an `AuditEvent` with a correlation id.
- [ ] **Timezone** — all datetimes are timezone-aware; cutoffs are computed in the rail's business timezone via `zoneinfo`; business code uses `app.core.clock.now()`.
- [ ] **Legacy parity** — fee or routing behaviour unchanged, or golden fixtures updated with an ADR note.

## Tests run

<!-- Paste the commands and a one-line result for each, e.g. `make test-api` -> 412 passed. -->

- [ ] `make lint`
- [ ] `make typecheck`
- [ ] `make test-api`
- [ ] `make test-web`
- [ ] `make test-e2e` (required for UI changes)
- [ ] `make seed-verify` (required for seed, policy or domain-rule changes)
- [ ] `make contracts` re-run; `shared/contracts/openapi.json` and generated types committed (required for API changes)

## Screenshots / recordings (UI changes)

<!-- Before / after. Include the scenario clock and the demo identity used. -->

## Reviewer notes

<!-- Where to start reading, known trade-offs, follow-ups, anything you want a second opinion on. -->
