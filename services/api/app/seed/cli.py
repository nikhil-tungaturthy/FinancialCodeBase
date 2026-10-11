"""Seed and verify the scenario database.

uv run python -m app.seed.cli seed
uv run python -m app.seed.cli verify
"""

from __future__ import annotations

import typer

from app.db.init import drop_database, init_database
from app.db.session import get_engine, session_scope
from app.seed.build import run_seed
from app.seed.verify import verify_seed

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def seed(
    force: bool = typer.Option(False, "--force", help="Drop and recreate a seeded database."),
) -> None:
    """Create the deterministic scenario. Skips work when the database is already seeded."""
    engine = get_engine()
    if force:
        drop_database(engine)
    init_database(engine)
    with session_scope(engine) as db_session:
        message = run_seed(db_session, force=False)
    typer.echo(message)


@app.command()
def verify() -> None:
    """Re-check seed invariants. Exits non-zero when any fail."""
    engine = get_engine()
    init_database(engine)
    with session_scope(engine) as db_session:
        problems = verify_seed(db_session)
    if problems:
        for problem in problems:
            typer.echo(f"FAIL  {problem}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Seed verification passed.")


if __name__ == "__main__":
    app()
