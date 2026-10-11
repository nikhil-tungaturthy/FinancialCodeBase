# Security posture

Meridian Flow is a demo. Treat it that way.

What it does:

- Demo identity is the `X-Demo-User` header. Unknown or inactive names get 401. Roles are checked on mutating routes.
- The requestor of an approval cannot decide it.
- Amounts are `Decimal`. Inputs that are floats are rejected at the money type.
- Errors are problem+json and include a correlation id. They do not include stack traces in the default handlers' client body beyond the problem fields.
- The database file is local SQLite. `.env` is gitignored. No tokens are stored in the repo.

What it is not:

- Not production authentication, session management, or network segmentation.
- Not a control that would satisfy a bank's access model. An engineer persona can read the desk; that is intentional for the demo.
- Not connected to a real payment network. Do not point it at one.
- Agent changes should be reviewed by a person before they are treated as a fix. Automations are instructed not to delete ledger rows or mark a discrepant batch reconciled.
