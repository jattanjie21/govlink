"""Tests for the Alembic migration infrastructure."""

from __future__ import annotations

import configparser
import sqlite3
from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config_for(database_url: str) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_alembic_ini_exists_and_is_valid() -> None:
    """``alembic.ini`` is a valid INI file with the expected ``script_location``."""
    ini_path = REPO_ROOT / "alembic.ini"
    assert ini_path.exists()
    parser = configparser.ConfigParser()
    parser.read(ini_path)
    assert parser["alembic"]["script_location"] == "alembic"


def test_alembic_env_py_imports_govlink_models() -> None:
    """``alembic/env.py`` references our project metadata source of truth."""
    env_path = REPO_ROOT / "alembic" / "env.py"
    text = env_path.read_text()
    assert "from govlink.db import Base" in text
    assert "target_metadata = Base.metadata" in text
    assert "auto_discover" in text  # loads dataset modules so all tables register


def test_initial_migration_exists() -> None:
    """At least one migration file is committed to ``alembic/versions/``."""
    versions = list((REPO_ROOT / "alembic" / "versions").glob("*.py"))
    assert len(versions) >= 1
    # Body sanity-check: the initial migration creates our four registry tables.
    initial_text = "\n".join(p.read_text() for p in versions)
    for table in ("datasets", "source_files", "ingestion_logs", "data_exchange_rates"):
        assert f"'{table}'" in initial_text or f'"{table}"' in initial_text


def test_migrations_upgrade_head_on_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``alembic upgrade head`` against a fresh SQLite creates the full schema."""
    db_path = tmp_path / "alembic_upgrade.db"
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    from govlink.config import get_settings

    get_settings.cache_clear()

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

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


def test_migrations_downgrade_to_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "alembic_downgrade.db"
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    from govlink.config import get_settings

    get_settings.cache_clear()

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()

    # alembic_version is left behind (Alembic's own table); our tables should be gone.
    assert "datasets" not in tables
    assert "data_exchange_rates" not in tables


def test_migrations_are_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Running ``upgrade head`` twice does not error (no-op the second time)."""
    db_path = tmp_path / "alembic_idem.db"
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    from govlink.config import get_settings

    get_settings.cache_clear()

    cfg = _alembic_config_for(f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # second call is a no-op
