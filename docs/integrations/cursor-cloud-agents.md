# Cursor Cloud Agents

A Cloud Agent needs a git remote it can clone and push to. This repository does not configure that remote. After you connect GitHub (or another host) in the Cursor dashboard:

1. Open the repo in Cursor and confirm the agent can run `make setup`.
2. The install step is `make setup` (uv sync, npm ci). No API keys.
3. Seed with `make seed` if the agent needs the database. Tests that call `run_seed` build their own in-memory database.
4. Verify with `make test`.
5. Ask the agent to implement MGB-318 on a new branch and open a pull request. Tell it the example batch is `SB-20260317-SEPA-02` and that `main` must stay free of the finished investigation.

`AGENTS.md` is the instruction file the agent should follow. Do not paste presenter-kit answer keys into the repo.

The start branch for this task is `demo/cloud-agent-start`, created from the `baseline-v1` tag by `make demo-branches`. A completed reference, if one has been built, is `demo/cloud-agent-completed` and is not merged to main.
