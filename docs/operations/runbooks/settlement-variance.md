# Runbook: settlement reconciliation variance

**Trigger.** A settlement batch moves to status `DISCREPANCY` after a reconciliation run, or an
incident with `service: meridian-batch/settlement` and a non-zero `variance` is opened
(`incident.opened` log line, `GET /api/v1/incidents`). Example: `INC-2026-0318-004` on
`SB-20260317-SEPA-02`.

**Owner.** Settlement & Reconciliation on-call analyst, with Payments Platform Engineering
on-call for anything that requires a code or data change. Finance Control approves any
correcting journal.

**Severity guide.** SEV2 when the variance is on a settled batch of the current or previous
value date (customer or nostro positions may be misstated); SEV3 when the batch is older and
the amount is below the rail's reporting threshold; SEV1 if the same symptom appears on more
than one batch in a run.

**Principles.** Do not delete rows. Do not re-run `settlement post-ledger` for a batch in
`DISCREPANCY`. Do not move the batch to `RECONCILED` by hand. Every action you take is recorded
as an audit event or an incident note.

---

## 1. Acknowledge and scope (first 10 minutes)

1. Open the incident: `GET /api/v1/incidents/{incident_ref}` or the Settlement page in the web
   app. Note `affected_batch`, `affected_payments`, `correlation_id`, `symptoms` and
   `evidence_path`.
2. Confirm the current state of the batch:
   ```bash
   curl -s -H 'X-Demo-User: aisha.bello' localhost:8000/api/v1/settlement/batches/SB-20260317-SEPA-02 | jq '.batch, .reconciliation'
   curl -s -H 'X-Demo-User: aisha.bello' localhost:8000/api/v1/reconciliation/summary | jq .
   ```
   Record `status`, `expected_total`, `recorded_total`, `variance`, `matched_count`,
   `unmatched_count`, `unmatched_refs` and the `run_ref` of the latest reconciliation result.
3. Check whether other batches in the same run are affected
   (`GET /api/v1/settlement/batches?status=DISCREPANCY`). More than one batch: raise severity
   and page engineering now.
4. Post an acknowledgement note on the incident with the figures above and the time you took
   over.

## 2. Collect evidence

1. Emit the evidence bundle and keep the output with the incident:
   ```bash
   make incident-emit            # or: python3 scripts/emit_incident.py INC-2026-0318-004
   ```
   It prints the payload, the per-file line counts and every warning/error line in the logs.
2. Pull the ledger rows for the batch and group them by settlement entry:
   ```bash
   curl -s -H 'X-Demo-User: aisha.bello' 'localhost:8000/api/v1/ledger/entries?batch_ref=SB-20260317-SEPA-02&page_size=200' \
     | jq -r '.items[] | select(.leg=="PRINCIPAL" and .direction=="CREDIT") | "\(.payment_id // .payment_ref) \(.journal_ref) \(.entry_ref) \(.amount)"' | sort
   ```
   A settlement entry with more than one principal credit, or none, explains a variance of
   that entry's amount. Cross-check every `unmatched_ref` against this list.
3. Read the posting run for the batch's correlation id. For the live system use the batch job
   log; for the incident fixture:
   ```bash
   jq -c 'select(.correlation_id=="corr-settle-20260318-sepa02" and (.level!="info" or .event=="ledger.posting_completed"))' \
     shared/fixtures/incidents/INC-2026-0318-004/settlement-run.jsonl
   jq -r 'select(.event=="ledger.posted") | "\(.entry_ref) \(.journal_ref) attempt=\(.attempt)"' \
     shared/fixtures/incidents/INC-2026-0318-004/settlement-run.jsonl | sort
   ```
   Record: `entry_count` vs `posted_count`, any `db.operation_timeout`, `ledger.retry`,
   `db.slow_transaction` lines, and which entries have more than one `ledger.posted` line.
4. Read the reconciliation run for the same batch
   (`reconciliation.variance_detected`, `batch.status_changed`) and note the
   `ledger_principal_credit_count` versus `settlement_entry_count`.
5. Check the audit trail for the batch and the affected payments:
   `GET /api/v1/audit?entity_ref=SB-20260317-SEPA-02` and
   `GET /api/v1/audit?correlation_id=corr-settle-20260318-sepa02`.
6. Verify journal balance for every journal involved (sum of debits equals sum of credits per
   `journal_ref`). An unbalanced journal is a separate, higher-severity problem.
7. Add an evidence note to the incident listing the refs you confirmed (settlement entry,
   journal refs, ledger entry refs, amounts, timestamps).

## 3. Contain

1. Leave the batch in `DISCREPANCY`. Payments in the batch remain `SETTLED`; do not transition
   them.
2. Make sure no further posting run will touch the batch (the posting job selects batches whose
   ledger is not yet posted; confirm with engineering that the batch is excluded until
   corrected).
3. If the variance affects a customer-facing balance for the current value date, inform the
   Payments Manager on duty (`elena.vasquez` in the demo roster) so the customer position can be
   explained if queried.
4. If the posting run reported `db.operation_timeout` or `db.slow_transaction`, ask engineering
   to check for concurrent writers on the database during the run window and to confirm the
   next nightly run will not overlap.

## 4. Correct

Corrections are journal entries, never edits or deletions, and are posted with
`posting_source = MANUAL` after Finance Control approval. The precedent is
`INC-2026-0305-002` (`SB-20260305-CHAPS-01`, missing principal posting corrected with a manual
journal through `2900-SUSPENSE-GBP`).

1. Prepare the correcting journal with Finance Control: for a surplus principal credit, a
   reversing journal that debits `2010-NOSTRO-{CCY}` and credits `1100-CUST-{CCY}` for the
   surplus amount, plus the reversal of any surplus fee legs (`4100-FEE-INCOME-{CCY}` debit,
   `1100-CUST-{CCY}` credit). Use the same `payment_id`, `batch_id`, value date and a
   description that names the incident and the journal being reversed.
2. Record the approval (who, when, amounts) as an incident note before posting.
3. Post the journal through the agreed manual-posting procedure, with the incident's
   `correlation_id`, so the audit event links back to the incident.
4. Re-run reconciliation for the batch:
   ```bash
   make batch-reconcile                       # value date 2026-03-17, all batches
   # or through the API (ANALYST or above):
   curl -s -X POST -H 'X-Demo-User: aisha.bello' localhost:8000/api/v1/settlement/batches/SB-20260317-SEPA-02/reconcile | jq .
   ```
   Each run appends a new `reconciliation_results` row; the latest row is the one that counts.
5. Compare the new result with the previous one. If the batch reconciles (`MATCHED`,
   `variance "0.00"`) it transitions to `RECONCILED` and its payments to `RECONCILED`. If the
   baseline matcher still reports the entry as unmatched after a reversing journal (it counts
   principal credits per settlement entry and does not net reversals), record that the
   financial position is corrected, keep the batch in `DISCREPANCY`, and open an engineering
   follow-up ticket referencing the incident.

## 5. Communicate

- Update the incident status (`INVESTIGATING` while evidence is being collected, `MITIGATED`
  once the correcting journal is posted, `RESOLVED` once reconciliation is clean or the
  residual is formally accepted).
- Post a summary in the settlement operations channel at acknowledgement, at mitigation and at
  resolution: batch, amount, affected payments, what was done, what remains.
- Notify the rail operations desk only if the nostro statement from the rail will not match
  the bank's expected position for the value date.

## 6. Close

1. Resolution summary on the incident: what was observed, the evidence refs, the correcting
   journal refs, the final reconciliation `run_ref`, and the owner of any follow-up ticket.
2. Hand over to Payments Platform Engineering for the post-incident review within two business
   days. Attach the evidence bundle (`make incident-emit`), the posting and reconciliation log
   extracts, and the list of entries that were posted more than once or not at all.
3. Confirm the next nightly posting and reconciliation runs complete with `retries 0` and no
   `DISCREPANCY` batches; note the result on the incident before closing.

## Reference

- Reconciliation semantics (baseline): a settlement entry is matched when exactly one ledger
  principal credit with an equal amount exists for its payment; everything else is listed in
  `unmatched_refs`; `variance = recorded_total - expected_total`.
- Ledger account codes: `1100-CUST-{CCY}` customer deposits, `2010-NOSTRO-{CCY}` nostro,
  `4100-FEE-INCOME-{CCY}` fee income, `2900-SUSPENSE-{CCY}` manual corrections.
- Evidence bundle layout: `shared/fixtures/incidents/README.md`.
- Related tickets: `docs/product/tickets/`.
