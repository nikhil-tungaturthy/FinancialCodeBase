# Demo reset

`make demo-reset` (`scripts/demo_reset.sh`) returns the local scenario database to its pristine,
deterministic state. Use it between demo runs, after local experiments that changed data, or
whenever `make seed-verify` reports a violation.

## What it does

1. Prints a warning box that names the exact file it will delete:
   `<repo>/data/meridian_flow.db` (or `DB_FILE` if overridden, see below).
2. Checks whether another process has the database open (`lsof`). If so it stops, because a
   running API would keep the old file open and continue serving stale data. Stop `make dev` /
   `make api` first, or pass `FORCE=1` to override.
3. Asks for confirmation: type `y` at the prompt, or run with `FORCE=1` (or `--force`) for
   non-interactive use. Without a terminal and without `FORCE=1` it aborts.
4. Deletes, if present:
   - `data/meridian_flow.db`
   - `data/meridian_flow.db-wal`
   - `data/meridian_flow.db-shm`
   - `data/meridian_flow.db-journal`
5. Runs `uv run python -m app.seed.cli seed`, which rebuilds the full scenario with
   `random.Random(20260318)`; repeated seeds produce identical rows.
6. Runs `uv run python -m app.seed.cli verify`, which re-derives the seed invariants and exits
   non-zero if any fail. The script's exit status is the verify status.

Typical duration is a few seconds.

## What it does not delete

- Source code, tests, fixtures (`shared/fixtures/**`), policies or documentation.
- `.env`, `.venv`, `node_modules`, caches, build outputs (`make clean` handles caches and build
  outputs; it also keeps `.venv`, `node_modules` and the database).
- Anything outside `data/`. The script refuses `DB_FILE` values that are absolute, contain `..`
  or a subdirectory, or do not end in `.db`, and it checks that the parent directory resolves to
  the repository's `data/` directory even through symlinks.
- Other files inside `data/` (for example `data/.gitkeep` or exports you placed there).
- Git state, branches, worktrees (`scripts/demo/create_worktrees.sh --remove` is separate and
  also non-destructive to branches).

## Usage

```bash
make demo-reset                 # interactive, asks for 'y'
make demo-reset FORCE=1         # no prompt (CI, scripts)
scripts/demo_reset.sh --force   # same
DB_FILE=data/scratch.db make demo-reset    # a different file, still inside data/
```

Expected tail of the output:

```
removed  /path/to/meridian-flow/data/meridian_flow.db
removed  /path/to/meridian-flow/data/meridian_flow.db-wal
removed  /path/to/meridian-flow/data/meridian_flow.db-shm

==> uv run python -m app.seed.cli seed
...
==> uv run python -m app.seed.cli verify
...
Demo database reset complete: /path/to/meridian-flow/data/meridian_flow.db
```

## After a reset

- Restart the API if it was running (`make dev` / `make api`) so it opens the new file; then
  `make ready` should report `seeded: true` with the current `seed_version`.
- The web app needs no action beyond a refresh.
- Demo identities, the hero payment `MGB-PAY-1042`, the incident `INC-2026-0318-004` and the
  discrepancy batch `SB-20260317-SEPA-02` are back exactly as documented.

## Troubleshooting

| Symptom                                                        | Cause / fix                                                                          |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `refusing to continue: DB_FILE must be a .db file directly inside data/` | `DB_FILE` is outside `data/` or malformed; use `data/<name>.db`           |
| `aborting while the database is open`                          | stop the API (`make dev`), or `FORCE=1`                                              |
| `no interactive terminal and FORCE is not set`                 | add `FORCE=1` when running from scripts or CI                                        |
| seed finishes but verify fails                                 | a domain or seed change broke an invariant; fix the code, do not edit the database   |
| `/ready` still shows the old `seed_version`                    | the API process still holds the old file; restart it                                 |
