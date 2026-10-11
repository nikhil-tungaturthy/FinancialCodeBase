# Testing

```bash
make test-api     # pytest: API, batch, legacy references
make test-web     # vitest
make test-e2e     # Playwright; needs `make dev` and `make ready`
make lint
make typecheck
```

`services/api/tests/integration/test_scenario.py` seeds an in-memory database and checks the hero payment, the name-mismatch failure, and the SEPA discrepancy figures.

`make seed-verify` checks the on-disk database: seed version, hero amount and fee, exception queue, batch variance, balanced journals, contiguous event sequences.

Legacy tests live in `legacy/reference-tests`. COBOL is executed when `cobc` is on `PATH`; otherwise those cases skip and the Python reference still runs. VB6 is not compiled here. The routing golden test compares the `.bas` source with the Python tables.

Known limits: end-to-end tests cover the shell, not every click. The discrepancy investigation in MGB-318 is not implemented, so there is no test for a classified break.
