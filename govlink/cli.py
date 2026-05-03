"""Typer-based CLI entrypoint for govlink.

Commands:

- ``govlink datasets list`` — list every registered dataset
- ``govlink db init`` — create the schema (SQLite only; Postgres uses Alembic)
- ``govlink ingest <slug>`` — run the orchestrator for one dataset
- ``govlink --version`` — print the package version
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from typing import Annotated

import typer
from sqlalchemy.exc import OperationalError

from govlink import __version__
from govlink.config import get_settings
from govlink.core.models import Dataset
from govlink.core.registry import DatasetNotFoundError, get_registry
from govlink.db import Base, get_engine, init_db
from govlink.ingestion.orchestrator import Orchestrator

app = typer.Typer(
    name="govlink",
    help="Open data API for Gambian government datasets.",
    no_args_is_help=True,
    add_completion=False,
)

datasets_app = typer.Typer(no_args_is_help=True, help="Inspect registered datasets.")
db_app = typer.Typer(no_args_is_help=True, help="Database management commands.")
app.add_typer(datasets_app, name="datasets")
app.add_typer(db_app, name="db")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"govlink {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Open data API for Gambian government datasets."""


@datasets_app.command("list")
def datasets_list() -> None:
    """List every registered dataset with title, frequency, and last ingestion."""
    registry = get_registry()
    registry.auto_discover()

    definitions = registry.list_all()
    if not definitions:
        typer.echo("No datasets registered.")
        return

    last_ingested_lookup = _last_ingested_lookup([d.slug for d in definitions])

    typer.echo(f"{'SLUG':<20}  {'FREQ':<10}  {'LAST INGESTED':<25}  TITLE")
    typer.echo("-" * 90)
    for d in definitions:
        last = last_ingested_lookup.get(d.slug, "never")
        typer.echo(f"{d.slug:<20}  {d.frequency.value:<10}  {last:<25}  {d.title}")


def _last_ingested_lookup(slugs: list[str]) -> dict[str, str]:
    """Best-effort lookup; returns 'never' for everything if the DB is unreachable."""
    try:
        init_db()
        engine = get_engine()
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            rows = session.execute(
                select(Dataset.slug, Dataset.last_ingested_at).where(Dataset.slug.in_(slugs))
            ).all()
        return {
            slug: (last.isoformat() if isinstance(last, datetime) else "never")
            for slug, last in rows
        }
    except (OperationalError, RuntimeError):
        return dict.fromkeys(slugs, "never")


@db_app.command("init")
def db_init() -> None:
    """Create all tables. Use Alembic for Postgres in production."""
    settings = get_settings()
    init_db()
    engine = get_engine()
    if engine.dialect.name != "sqlite":
        typer.echo("Postgres detected — use `alembic upgrade head` for production migrations.")
        raise typer.Exit()

    # Auto-discover so every dataset's model module loads and Base.metadata
    # knows about its data table before create_all runs.
    get_registry().auto_discover()
    Base.metadata.create_all(engine)
    typer.echo(f"Database initialised at {settings.database_url}")


@app.command("ingest")
def ingest(
    slug: Annotated[str, typer.Argument(help="Dataset slug to ingest.")],
    backfill_from: Annotated[
        datetime | None,
        typer.Option(
            "--backfill-from",
            help="Process all files from this date onwards (YYYY-MM-DD).",
            formats=["%Y-%m-%d"],
        ),
    ] = None,
) -> None:
    """Run one ingestion cycle for the named dataset."""
    registry = get_registry()
    registry.auto_discover()
    try:
        definition = registry.get(slug)
    except DatasetNotFoundError:
        typer.echo(f"Unknown dataset: {slug!r}", err=True)
        raise typer.Exit(code=1) from None

    settings = get_settings()
    init_db()
    engine = get_engine()
    Base.metadata.create_all(engine)

    backfill_date: date | None = backfill_from.date() if backfill_from else None

    from sqlalchemy.orm import Session

    with Session(engine, expire_on_commit=False) as session:
        orchestrator = Orchestrator(session=session, raw_data_dir=settings.raw_data_dir)
        try:
            summary = orchestrator.ingest(
                definition,
                latest=backfill_date is None,
                backfill_from=backfill_date,
            )
        except Exception as e:
            typer.echo(f"Ingestion failed: {e}", err=True)
            raise typer.Exit(code=1) from e

    typer.echo(
        f"Dataset:        {summary.dataset_slug}\n"
        f"Discovered:     {summary.files_discovered}\n"
        f"Skipped:        {summary.files_skipped}\n"
        f"Ingested:       {summary.files_ingested}\n"
        f"Failed:         {summary.files_failed}\n"
        f"Rows added:     {summary.total_rows_added}\n"
        f"Duration:       {summary.duration_seconds:.2f}s"
    )
    if summary.files_failed > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
