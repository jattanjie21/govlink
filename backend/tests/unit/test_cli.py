"""Tests for govlink.cli — Typer CLI."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from govlink.cli import app
from govlink.core.registry import DatasetRegistry
from govlink.ingestion.orchestrator import IngestionSummary

runner = CliRunner()

_DATASET_MODULE = "govlink.datasets.exchange_rates.dataset"


def _force_dataset_reregistration() -> None:
    """Pop the dataset module so the next ``auto_discover`` re-runs registration.

    The ``isolated_global_registry`` fixture swaps the global registry, but
    Python's import cache means a re-imported ``dataset.py`` won't fire its
    ``register()`` side effect a second time. Popping the module forces the
    next ``importlib.import_module`` call inside ``auto_discover`` to run
    the body and register against the freshly-isolated global.
    """
    import sys

    sys.modules.pop(_DATASET_MODULE, None)


# --- general ----------------------------------------------------------------


def test_cli_help_shows_available_commands(mock_settings: object) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "datasets" in result.stdout
    assert "db" in result.stdout


def test_cli_version_flag(mock_settings: object) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "govlink 0.1.0" in result.stdout


# --- datasets list ----------------------------------------------------------


def test_datasets_list_shows_registered_datasets(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    """``datasets list`` reports every registered dataset's slug, title, frequency."""
    _force_dataset_reregistration()
    result = runner.invoke(app, ["datasets", "list"])
    assert result.exit_code == 0
    assert "exchange-rates" in result.stdout
    assert "Daily Valuation Exchange Rates" in result.stdout
    assert "daily" in result.stdout.lower()


def test_datasets_list_empty_when_none_registered(
    isolated_global_registry: DatasetRegistry,
    mock_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no datasets registered, the command reports 'No datasets registered'."""
    # Suppress auto-discovery so the registry stays empty.
    from govlink.core.registry import DatasetRegistry as _Registry

    monkeypatch.setattr(_Registry, "auto_discover", lambda *_a, **_kw: None)
    result = runner.invoke(app, ["datasets", "list"])
    assert result.exit_code == 0
    assert "No datasets registered" in result.stdout


# --- db init ----------------------------------------------------------------


def test_db_init_creates_tables_in_sqlite(mock_settings: object, tmp_path: Path) -> None:
    """``db init`` creates the full schema in a fresh SQLite file."""
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0, result.stdout

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()

    expected = {
        "datasets",
        "dataset_fields",
        "source_files",
        "ingestion_logs",
        "data_exchange_rates",
    }
    assert expected.issubset(tables)


def test_db_init_is_idempotent(mock_settings: object) -> None:
    """Running ``db init`` twice does not error."""
    first = runner.invoke(app, ["db", "init"])
    assert first.exit_code == 0
    second = runner.invoke(app, ["db", "init"])
    assert second.exit_code == 0


# --- ingest -----------------------------------------------------------------


def test_ingest_latest_runs_orchestrator(
    isolated_global_registry: DatasetRegistry,
    mock_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``govlink ingest exchange-rates`` invokes orchestrator with latest=True."""
    fake_summary = IngestionSummary(
        dataset_slug="exchange-rates",
        files_discovered=1,
        files_skipped=0,
        files_ingested=1,
        files_failed=0,
        total_rows_added=33,
        duration_seconds=0.5,
    )
    mock_orch = MagicMock()
    mock_orch.ingest.return_value = fake_summary

    _force_dataset_reregistration()
    with patch("govlink.cli.Orchestrator", return_value=mock_orch) as orch_cls:
        result = runner.invoke(app, ["ingest", "exchange-rates"])

    assert result.exit_code == 0, result.stdout
    orch_cls.assert_called_once()
    mock_orch.ingest.assert_called_once()
    _args, kwargs = mock_orch.ingest.call_args
    assert kwargs.get("latest") is True
    assert kwargs.get("backfill_from") is None


def test_ingest_with_backfill_from_flag(
    isolated_global_registry: DatasetRegistry,
    mock_settings: object,
) -> None:
    fake_summary = IngestionSummary(
        dataset_slug="exchange-rates",
        files_discovered=10,
        files_skipped=0,
        files_ingested=10,
        files_failed=0,
        total_rows_added=330,
        duration_seconds=4.2,
    )
    mock_orch = MagicMock()
    mock_orch.ingest.return_value = fake_summary

    _force_dataset_reregistration()
    with patch("govlink.cli.Orchestrator", return_value=mock_orch):
        result = runner.invoke(app, ["ingest", "exchange-rates", "--backfill-from", "2025-01-01"])

    assert result.exit_code == 0, result.stdout
    _args, kwargs = mock_orch.ingest.call_args
    assert kwargs.get("backfill_from") == date(2025, 1, 1)
    assert kwargs.get("latest") is False


def test_ingest_unknown_dataset_errors(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    """Ingesting a non-existent dataset exits non-zero with a clear message."""
    result = runner.invoke(app, ["ingest", "nonexistent-slug"])
    assert result.exit_code != 0
    assert "nonexistent-slug" in result.stdout or "nonexistent-slug" in (result.stderr or "")


def test_ingest_shows_summary_on_success(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    fake_summary = IngestionSummary(
        dataset_slug="exchange-rates",
        files_discovered=2,
        files_skipped=1,
        files_ingested=1,
        files_failed=0,
        total_rows_added=33,
        duration_seconds=1.234,
    )
    mock_orch = MagicMock()
    mock_orch.ingest.return_value = fake_summary

    _force_dataset_reregistration()
    with patch("govlink.cli.Orchestrator", return_value=mock_orch):
        result = runner.invoke(app, ["ingest", "exchange-rates"])

    assert result.exit_code == 0, result.stdout
    out = result.stdout
    assert "exchange-rates" in out
    assert "1" in out  # files_ingested
    assert "33" in out  # rows_added


def test_ingest_shows_error_on_failure(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    """If the orchestrator raises, the CLI catches, prints, and exits 1."""
    mock_orch = MagicMock()
    mock_orch.ingest.side_effect = RuntimeError("boom — listing fetch failed")

    _force_dataset_reregistration()
    with patch("govlink.cli.Orchestrator", return_value=mock_orch):
        result = runner.invoke(app, ["ingest", "exchange-rates"])

    assert result.exit_code == 1
    assert "boom" in result.stdout or "boom" in (result.stderr or "")


def test_datasets_list_renders_last_ingested_when_db_has_dataset_row(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    """When the DB IS initialised and Dataset rows exist, ``last_ingested_at`` is rendered."""
    # Initialise schema and seed a Dataset row so the lookup hits the success branch.
    runner.invoke(app, ["db", "init"])
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from govlink.core.models import Dataset, DatasetFrequency
    from govlink.db import get_engine

    with Session(get_engine(), expire_on_commit=False) as session:
        session.add(
            Dataset(
                slug="exchange-rates",
                title="Daily Valuation Exchange Rates",
                publisher="Central Bank of The Gambia",
                source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
                frequency=DatasetFrequency.DAILY,
                last_ingested_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            )
        )
        session.commit()

    _force_dataset_reregistration()
    result = runner.invoke(app, ["datasets", "list"])
    assert result.exit_code == 0
    # Stringified ISO date is present (full timestamp may vary by tz handling).
    assert "2026-04-30" in result.stdout


def test_db_init_postgres_routes_to_alembic_message(
    mock_settings: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``db init`` against Postgres prints the Alembic-instead message."""
    from sqlalchemy.engine import Engine

    fake_engine = MagicMock(spec=Engine)
    fake_engine.dialect = MagicMock()
    fake_engine.dialect.name = "postgresql"
    monkeypatch.setattr("govlink.cli.get_engine", lambda: fake_engine)
    monkeypatch.setattr("govlink.cli.init_db", lambda: None)

    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0
    assert "alembic upgrade head" in result.stdout


def test_ingest_exits_nonzero_when_files_failed(
    isolated_global_registry: DatasetRegistry, mock_settings: object
) -> None:
    """If the orchestrator reports failed files, the CLI exits with code 1."""
    fake_summary = IngestionSummary(
        dataset_slug="exchange-rates",
        files_discovered=2,
        files_skipped=0,
        files_ingested=1,
        files_failed=1,
        total_rows_added=33,
        duration_seconds=0.5,
    )
    mock_orch = MagicMock()
    mock_orch.ingest.return_value = fake_summary

    _force_dataset_reregistration()
    with patch("govlink.cli.Orchestrator", return_value=mock_orch):
        result = runner.invoke(app, ["ingest", "exchange-rates"])

    assert result.exit_code == 1


def test_datasets_list_shows_never_when_db_uninitialized(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """When no DB is initialised, last_ingested_at is rendered as 'never'."""
    # Use a settings env that points to a non-existent SQLite path.
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{tmp_path / 'nope.db'}")
    monkeypatch.setenv("GOVLINK_RAW_DATA_DIR", str(tmp_path / "raw"))
    from govlink.config import get_settings

    get_settings.cache_clear()
    try:
        _force_dataset_reregistration()
        result = runner.invoke(app, ["datasets", "list"])
        assert result.exit_code == 0
        assert "never" in result.stdout.lower()
    finally:
        get_settings.cache_clear()
