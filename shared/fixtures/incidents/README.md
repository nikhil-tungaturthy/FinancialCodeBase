# Incident evidence fixtures

One directory per operational incident, named after its `incident_ref`. Each directory is a
self-contained evidence bundle that the API (`GET /api/v1/incidents/{ref}`) references through
`evidence_path`, that `scripts/emit_incident.py` reads, and that the on-call runbooks point at.
All content is synthetic.

| Incident            | Status | Severity | Service                      | Summary                                                   |
| ------------------- | ------ | -------- | ---------------------------- | --------------------------------------------------------- |
| `INC-2026-0318-004` | OPEN   | SEV2     | `meridian-batch/settlement`  | Reconciliation variance of +18,450.00 EUR on `SB-20260317-SEPA-02` |

## Layout

```
shared/fixtures/incidents/
  README.md                      this file
  <INCIDENT_REF>/
    incident.json                the incident payload (schema below)
    *.jsonl                      structured log extracts, one JSON object per line
    README.md                    what each file is, how it was captured, how to read it
```

## `incident.json`

| Field               | Type           | Meaning                                                                 |
| ------------------- | -------------- | ----------------------------------------------------------------------- |
| `incident_id`       | string         | `INC-YYYY-MMDD-NNN`; must equal the directory name                      |
| `opened_at`         | ISO-8601 UTC   | when the incident record was created                                    |
| `severity`          | enum           | `SEV1` … `SEV4`                                                         |
| `status`            | enum           | `OPEN`, `INVESTIGATING`, `MITIGATED`, `RESOLVED`                        |
| `service`           | string         | emitting service and component, e.g. `meridian-batch/settlement`        |
| `title`             | string         | one-line factual title                                                  |
| `affected_batch`    | string or null | settlement `batch_ref`                                                  |
| `affected_payments` | string[]       | `payment_ref`s under review                                             |
| `correlation_id`    | string         | correlation id of the run that produced the symptoms                    |
| `symptoms`          | string[]       | observed facts only; no hypotheses, no root cause                       |
| `evidence.logs`     | string[]       | log files in this directory                                             |
| `evidence.repo_paths` | string[]     | repository paths relevant to the investigation                          |
| `runbook`           | string         | repository path of the runbook to follow                                |
| `automation`        | object         | `suggested_instruction_ref`: docs path describing automation hooks      |

Optional fields used by some incidents: `opened_by`, `updated_at`, `updated_by`,
`reconciliation` (the reconciliation result that triggered the incident) and `related_refs`
(entry, journal and ledger refs mentioned in the symptoms). Amounts are strings with the
currency's minor units, never numbers.

## Log files

Log extracts follow the application logging schema (`docs/operations/local-development.md`,
"Logging"): `timestamp`, `level`, `event`, `logger`, `service`, `correlation_id`, plus
contextual fields such as `batch_ref`, `payment_ref`, `entry_ref`, `journal_ref`, `duration_ms`.
Lines are in time order. Each incident README states the filter that was used to export them.

## Tooling

```bash
make incident-emit                                   # pretty summary of INC-2026-0318-004 with log statistics
python3 scripts/emit_incident.py INC-2026-0318-004 --format json | jq .
python3 scripts/emit_incident.py --list
```

`emit_incident.py` validates the payload keys, checks that every referenced log exists, parses
every line and verifies the required log fields and time ordering; it exits 3 when a fixture is
malformed. It performs no network I/O unless `--webhook-url` is passed explicitly.

## Adding an incident

1. Create `shared/fixtures/incidents/<INCIDENT_REF>/` with `incident.json`, the log extracts
   and a `README.md`.
2. Keep symptoms factual and keep amounts, refs and timestamps consistent across the payload,
   the logs and the seeded database.
3. Run `python3 scripts/emit_incident.py <INCIDENT_REF>` to validate the bundle.
4. Seed the matching `operational_incidents` row (`evidence_path` points at the directory).
