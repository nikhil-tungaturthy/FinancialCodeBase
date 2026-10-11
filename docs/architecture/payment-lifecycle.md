# Payment lifecycle

```
CREATED → VALIDATING → APPROVED → PROCESSING → PENDING_SETTLEMENT → SETTLED → RECONCILED
                    ↘ HELD
                    ↘ REJECTED
HELD → APPROVED | CANCELLED | REJECTED | VALIDATING
APPROVED → PROCESSING | CANCELLED
PROCESSING → PENDING_SETTLEMENT | FAILED
PENDING_SETTLEMENT → SETTLED | FAILED
```

`RECONCILED`, `FAILED`, `CANCELLED` and `REJECTED` are terminal. Services call `assert_transition` before writing a new status. An illegal move is HTTP 409.

Validation runs the rules in `domain.validation.engine`. The primary failure opens one exception. Queue and severity are copied from `classify_exception`, which reproduces the retired review desk. The reason text, allowed actions and evidence list live in `domain/policies/exception_reasons.json`.

A release that the desk would have sent to a supervisor creates an approval instead of moving the payment. The requestor cannot decide their own approval. Approving applies the stored action; rejecting returns the exception to review.

Settlement windows are chosen in the rail's timezone. At the scenario clock (18:40 UTC on 18 March 2026) the USD wire window is still open and closes in 110 minutes (16:30 New York, EDT).

Daily reconciliation records expected total, recorded principal credits, variance and unmatched refs. Replaying the same inputs returns the existing run.
