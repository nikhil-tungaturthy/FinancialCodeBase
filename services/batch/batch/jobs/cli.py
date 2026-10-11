"""Batch job entry point.

uv run python -m batch.jobs.cli reconciliation run --value-date 2026-03-17
"""

from __future__ import annotations

from datetime import date

import typer

from app.db.init import init_database
from app.db.session import get_engine, session_scope
from batch.reconciliation.daily_reconciliation import reconcile_value_date

app = typer.Typer(add_completion=False, no_args_is_help=True)
reconciliation_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(reconciliation_app, name="reconciliation")


@reconciliation_app.command("run")
def run_reconciliation(
    value_date: str = typer.Option(..., "--value-date", help="Value date, YYYY-MM-DD."),
) -> None:
    """Reconcile settled batches for one value date."""
    parsed = date.fromisoformat(value_date)
    engine = get_engine()
    init_database(engine)
    with session_scope(engine) as db_session:
        count = reconcile_value_date(db_session, parsed)
    typer.echo(f"Reconciled {count} batch(es) for {parsed.isoformat()}.")


if __name__ == "__main__":
    app()
