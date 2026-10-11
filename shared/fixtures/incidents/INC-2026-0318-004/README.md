# INC-2026-0318-004 — Settlement reconciliation variance on SB-20260317-SEPA-02

| Field              | Value                                                      |
| ------------------ | ---------------------------------------------------------- |
| Opened             | 2026-03-18T01:42:17Z by `system` (reconciliation job)      |
| Severity / status  | SEV2 / OPEN                                                |
| Service            | `meridian-batch/settlement`                                |
| Batch              | `SB-20260317-SEPA-02` (SEPA_EUR, value date 2026-03-17, 17 entries, settled 2026-03-17T23:58:30Z) |
| Correlation id     | `corr-settle-20260318-sepa02`                              |
| Variance           | +18,450.00 EUR (expected 235,367.00, recorded 253,817.00)  |
| Affected payments  | `MGB-PAY-5143` (variance), `MGB-PAY-5140` and `MGB-PAY-5147` (adjacent entries, manual verification) |
| Last updated       | 2026-03-18T07:05:49Z by `aisha.bello` (added the two adjacent payments) |
| Runbook            | `docs/operations/runbooks/settlement-variance.md`          |

## Files

### `incident.json`

The incident payload as served by `GET /api/v1/incidents/INC-2026-0318-004` and emitted by
`scripts/emit_incident.py`. Symptoms are observations only. The `reconciliation` object is the
result row `RR-000061`; `related_refs` lists the settlement entry, journal refs and ledger entry
refs named in the symptoms.

### `settlement-run.jsonl` (35 lines)

Extract from the `meridian-batch` log for the nightly ledger posting job
(`settlement post-ledger --value-date 2026-03-17`), job start 2026-03-18T01:15:00.084Z, job end
01:17:10.718Z. The job posted ledger journals for the six value-date-2026-03-17 batches in
`settled_at` order; `SB-20260317-SEPA-02` was the last.

Export filter: all lines where `correlation_id == "corr-settle-20260318-sepa02"` (the
`SB-20260317-SEPA-02` posting) plus every line from logger `batch.jobs.cli` (job start, batch
selection, per-batch completion summaries, job end). Per-entry lines of the other five batches
are therefore not included. Level `info` and above.

What the lines show, in order:

1. `job.started`, `db.connected` (SQLite, WAL, `busy_timeout_ms` 5000), `settlement.batches_selected` (6 batches).
2. Five `job.batch_completed` summaries for `ACH-01`, `SWIFT-01`, `CHAPS-01`, `SEPA-01`, `WIRE-01`, each with `posted_count == entry_count` and `retries 0`.
3. `ledger.posting_started` for `SB-20260317-SEPA-02` at 01:16:54.521Z (`entry_count` 17, `expected_total` "235367.00").
4. `ledger.posted` for entries `SE-000380` … `SE-000387` (sequence 1–8), one journal each (`JRN-000604` … `JRN-000611`), each with the four `ledger_entry_refs` it created (principal debit/credit, fee debit/credit).
5. Entry `SE-000388` / `MGB-PAY-5143` (EUR 18,450.00):
   - `db.slow_transaction` (ledger insert, 3,973 ms) then `ledger.posted` with `journal_ref JRN-000612` at 01:17:03.412Z, `attempt 1`;
   - `db.operation_timeout` at 01:17:08.447Z: `sqlite3.OperationalError: database is locked` on `audit_events.insert`, `attempt 1`, `waited_ms` 5003;
   - `ledger.retry` `attempt 2` (`max_attempts` 3, `sleep_ms` 500);
   - `ledger.posted` with `journal_ref JRN-000613` at 01:17:09.118Z, `attempt 2`, `sequence 9`.
6. `ledger.posted` for `SE-000389` … `SE-000396` (sequence 10–17, `JRN-000614` … `JRN-000621`); `SE-000389` carries a `db.slow_transaction` warning (1,105 ms), the rest complete in under 50 ms.
7. `ledger.posting_completed`: `entry_count 17`, `posted_count 18`, `ledger_rows 72`, `retries 1`, `failures 0`; `audit.recorded` (`LEDGER_POSTED`); `job.batch_completed`; `job.completed` with `exit_code 0`.

### `reconciliation-run.jsonl` (32 lines)

Extract from the nightly reconciliation job (`reconciliation run --value-date 2026-03-17`),
job start 2026-03-18T01:42:00.917Z, job end 01:42:17.202Z. Same export rule: lines with the
batch's correlation id plus the job-level lines; the five other batches are represented by
their `batch_started` / `completed` / `status_changed` / `audit.recorded` lines because their
per-batch correlation ids are different.

1. `job.started`, `db.connected`, `reconciliation.batches_selected` (6 batches, `settled_at` order).
2. For `ACH-01`, `SWIFT-01`, `CHAPS-01`, `SEPA-01`, `WIRE-01`: `reconciliation.completed` with `status MATCHED`, `variance "0.00"`, then `batch.status_changed SETTLED -> RECONCILED` with the payments transitioned, then `audit.recorded` (`RECONCILIATION_RUN`, runs `RR-000056` … `RR-000060`).
3. For `SB-20260317-SEPA-02`:
   - `reconciliation.batch_started` with `settlement_entry_count 17` and `ledger_principal_credit_count 18`;
   - `reconciliation.variance_detected` at 01:42:16.702Z: `expected_total "235367.00"`, `recorded_total "253817.00"`, `variance "18450.00"`, `matched_count 16`, `unmatched_count 2`, `unmatched_refs ["LE-002448", "LE-002452"]`;
   - `reconciliation.completed` `status UNMATCHED`, `run_ref RR-000061`, `input_hash` recorded;
   - `batch.status_changed SETTLED -> DISCREPANCY` (`payments_transitioned 0`; the 17 payments stay `SETTLED`);
   - `audit.recorded` (`RECONCILIATION_RUN`), `incident.opened INC-2026-0318-004` at 01:42:17.000Z (`affected_payment_refs ["MGB-PAY-5143"]` at opening time), `audit.recorded` (`INCIDENT_OPENED`).
4. `reconciliation.report_written` (5 matched, 1 discrepancy) and `job.completed`.

## Cross-references

- `LE-002448` is the principal credit (`2010-NOSTRO-EUR`) of journal `JRN-000612`; `LE-002452` is the principal credit of `JRN-000613`. Both belong to `payment_ref MGB-PAY-5143`, `entry_ref SE-000388`, `batch_ref SB-20260317-SEPA-02`, `correlation_id corr-settle-20260318-sepa02`.
- `ledger_entry_refs` on each `ledger.posted` line are the four legs created for that journal, in the order principal debit (`1100-CUST-EUR`), principal credit (`2010-NOSTRO-EUR`), fee debit (`1100-CUST-EUR`), fee credit (`4100-FEE-INCOME-EUR`).
- Expected total 235,367.00 EUR is the sum of the 17 settlement entry amounts listed on the `ledger.posted` lines; recorded total 253,817.00 EUR is the sum of the 18 principal credits.
- Repository paths referenced by the payload: `services/batch/batch/settlement/ledger_poster.py`, `services/batch/batch/reconciliation/daily_reconciliation.py`, `services/api/app/models/ledger.py`.

## Reading the logs

```bash
# every line about the settlement entry that shows the variance
jq -c 'select(.entry_ref == "SE-000388")' shared/fixtures/incidents/INC-2026-0318-004/settlement-run.jsonl

# journals per settlement entry (an entry with more than one line was posted more than once)
jq -r 'select(.event == "ledger.posted") | "\(.entry_ref) \(.journal_ref) \(.attempt)"' \
  shared/fixtures/incidents/INC-2026-0318-004/settlement-run.jsonl | sort | uniq -c | awk '$1 > 1'

# warnings and errors across both runs
jq -c 'select(.level != "info")' shared/fixtures/incidents/INC-2026-0318-004/*.jsonl

# the whole bundle, validated, with per-file statistics
python3 scripts/emit_incident.py INC-2026-0318-004
```

All identifiers, amounts and timestamps are synthetic and belong to the Meridian Flow scenario
(scenario day Wednesday 2026-03-18).
