# Security Policy

## Scope of this project

Meridian Flow is a demonstration system. It processes **synthetic data only**: every customer,
account, beneficiary, payment, ledger entry and incident in the repository and in the seeded
database is fictional and generated deterministically. The application has no connection to
payment rails, banks, screening providers or any other external service, and it holds no
credentials or secrets. Nothing in this repository can move money or expose real personal data.

Because of that, the security posture is that of a local development tool:

- The API binds to `localhost` and uses a **demo identity header** (`X-Demo-User`). This is not
  authentication and is documented as such; do not expose the API beyond a trusted machine.
- The database is a local SQLite file under `data/` (gitignored).
- No TLS, rate limiting or secret management is provided or expected.

## Reporting a vulnerability

We still want to hear about real weaknesses in the code, the tooling or the CI configuration,
for example:

- dependency vulnerabilities that affect the runtime (not only dev tooling),
- injection, path traversal or deserialization issues in the API, batch jobs or scripts,
- CI workflow issues (secrets exposure, unsafe `pull_request_target` usage, unpinned actions),
- anything that would make the demo unsafe to run on a shared machine.

Please report privately rather than in a public issue:

1. Use GitHub's **private vulnerability reporting** on the repository ("Report a vulnerability"
   under the Security tab) if it is enabled for the fork you are working with; or
2. e-mail the platform engineering owners listed in `.github/CODEOWNERS` through your
   organisation's usual channel.

Include the affected path, a reproduction and the impact you see. We acknowledge reports within
five working days and keep you informed until the issue is resolved or declined with a reason.
Fixes ship as normal pull requests and are noted in the changelog section of the release notes.

## Out of scope

The following are known properties of the demo and are not security findings:

- `X-Demo-User` header identity and the ability to switch users from the UI.
- Absence of TLS, CSRF protection, session management or rate limiting on the local API.
- Permissions of the local SQLite file and of `data/`.
- Denial of service against the local development servers.
- Vulnerabilities only reachable through development-time tooling (linters, test runners,
  build tools) that is not part of the running application.
- Behaviours that are intentionally part of the demo scenario and tracked as product tickets in
  `docs/product/tickets/`.

## Dependency hygiene

Dependabot (`.github/dependabot.yml`) opens weekly update PRs for npm, Python (uv) and GitHub
Actions. Actions in CI are pinned to a major tag or a commit SHA. `uv.lock` and
`package-lock.json` are committed and installed with `uv sync --locked` / `npm ci` in CI.
