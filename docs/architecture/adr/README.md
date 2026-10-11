# Architecture decision records

Decisions that shape Meridian Flow, in the order they were made. Each record
states the context, the decision and its consequences; superseded records are
kept and marked, never deleted.

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-monorepo-and-stack.md) | Monorepo and technology stack | Accepted | 2026-03-02 |
| [0002](0002-scenario-clock-and-deterministic-seed.md) | Scenario clock and deterministic seed | Accepted | 2026-03-04 |
| [0003](0003-legacy-fee-and-routing-modernization.md) | Modernizing the legacy fee tariff (COBOL) and exception routing (VB6) | Accepted | 2026-03-09 |

## Writing a new record

* File name `NNNN-short-title.md`, next free number, lower-case kebab title.
* Sections: header (status, date, deciders, related), Context, Decision,
  Consequences. Add Validation and Risks sections when the decision changes
  observable behavior.
* Status is one of Proposed, Accepted, Superseded by NNNN, Deprecated.
* Link the record from this index and from the architecture document it
  affects.
