# Automations

MGB-502 is the incident a Cursor Automation can investigate. No automation is installed by this repository. Creating one is done in Cursor (Automations) and needs your account.

## Suggested trigger

A webhook or a manual run that receives the payload from:

```bash
make incident-emit
```

That command reads `shared/fixtures/incidents/INC-2026-0318-004` and prints the incident plus its log summary. It does not post anywhere unless you pass `--webhook-url` and confirm.

## What the automation should be allowed to do

1. Read the incident payload and the two JSONL logs.
2. Read `services/batch/batch/settlement/ledger_poster.py` and `services/batch/batch/reconciliation/daily_reconciliation.py`.
3. Read the batch `SB-20260317-SEPA-02` via the API or the seed.
4. Write a short hypothesis: which payment was posted twice, and why the job still exited 0.
5. Propose a guard (the current poster already skips a payment that has a principal credit; a unique constraint is the change worth discussing).
6. Open a draft pull request only if you have connected a git host.
7. Leave approval and any data repair to a person.

## Failure modes

- The database file is missing: run `make seed`.
- The agent deletes ledger rows or re-posts the batch: stop it. The runbook forbids both.
- The webhook URL is not an address you control: `emit_incident.py` refuses unexpected URLs.

Prompt sketch, for the automation instruction:

"Investigate INC-2026-0318-004 using the fixture logs and the settlement code. Explain the variance on SB-20260317-SEPA-02. Do not modify the database. If you propose a code change, open it as a draft and say what you did not verify."
