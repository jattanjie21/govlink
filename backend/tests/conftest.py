"""Pytest configuration and shared fixtures.

Shared fixtures for database sessions, FastAPI test client,
sample PDFs, and registry isolation live here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Side-effect import: registers ``data_exchange_rates`` with ``Base.metadata`` so
# ``in_memory_engine``'s ``create_all`` includes it. Importing the model module
# (not the dataset module) avoids touching the global registry, which would
# leak state into tests that expect an empty registry.
import govlink.datasets.exchange_rates.model  # noqa: F401
from govlink.core.registry import DatasetRegistry
from govlink.db import Base, create_engine_from_url


@pytest.fixture
def settings_env(monkeypatch: pytest.MonkeyPatch) -> Generator[pytest.MonkeyPatch, None, None]:
    """Yield ``monkeypatch`` with the ``get_settings`` lru_cache cleared.

    The cache is cleared both before and after the test so that no env var
    state — set explicitly here or leaked from a previous test — survives
    across tests. Use this for any test that mutates ``GOVLINK_*`` env vars
    and observes ``Settings`` behaviour.
    """
    from govlink.config import get_settings

    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory suitable for use as ``raw_data_dir``.

    Wraps pytest's built-in ``tmp_path`` and exposes it as a ``Path``
    with an unambiguous name for tests that need a writable data root.
    """
    data_dir = tmp_path / "raw"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def in_memory_engine() -> Generator[Engine, None, None]:
    """Yield a fresh in-memory SQLite engine with all ORM tables created.

    The engine is fully isolated per test (function scope) and is disposed
    after the test completes. Use together with ``db_session`` for ORM tests.
    """
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(in_memory_engine: Engine) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy ``Session`` bound to the in-memory test engine.

    Uses ``expire_on_commit=False`` so test assertions can read attributes
    after a commit without triggering a refresh. The session is closed in
    a ``finally`` block to mirror the ``get_session`` dependency.
    """
    factory = sessionmaker(bind=in_memory_engine, expire_on_commit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fresh_registry() -> DatasetRegistry:
    """A fresh ``DatasetRegistry`` instance, isolated from the global one.

    Use this for unit tests that exercise registry methods directly.
    Does not touch the process-global registry.
    """
    return DatasetRegistry()


@pytest.fixture
def isolated_global_registry() -> Generator[DatasetRegistry, None, None]:
    """Replace the process-global registry with a fresh one for one test.

    Use this when the code under test calls :func:`get_registry()`
    internally (notably the ``auto_discover`` tests). The original
    global is restored in a ``finally`` block so test order doesn't
    leak state.
    """
    from govlink.core import registry as _registry_module

    original = _registry_module._global_registry
    fresh = _registry_module.DatasetRegistry()
    _registry_module._global_registry = fresh
    try:
        yield fresh
    finally:
        _registry_module._global_registry = original


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to ``tests/fixtures/`` for tests that load real PDFs/HTML."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_pdf_fixture(fixtures_dir: Path) -> Callable[[str], bytes]:
    """Return a callable that reads the bytes of a fixture PDF by stem."""

    def _load(stem: str) -> bytes:
        return (fixtures_dir / "pdfs" / f"{stem}.pdf").read_bytes()

    return _load


@pytest.fixture
def load_pdf_expected(fixtures_dir: Path) -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads the expected-output JSON oracle for a PDF stem."""

    def _load(stem: str) -> dict[str, Any]:
        return json.loads((fixtures_dir / "pdfs" / f"{stem}.expected.json").read_text())

    return _load


@pytest.fixture
def load_html_fixture(fixtures_dir: Path) -> Callable[[str], str]:
    """Return a callable that reads the contents of an HTML fixture by file name."""

    def _load(name: str) -> str:
        return (fixtures_dir / "html" / name).read_text(encoding="utf-8")

    return _load


@pytest.fixture
def load_html_expected(fixtures_dir: Path) -> Callable[[str], dict[str, Any]]:
    """Return a callable that loads the expected-output JSON oracle for an HTML fixture."""

    def _load(stem: str) -> dict[str, Any]:
        return json.loads((fixtures_dir / "html" / f"{stem}.expected.json").read_text())

    return _load


@pytest.fixture
def initialized_db(in_memory_engine: Engine, db_session: Session) -> Session:
    """Yield a Session bound to an in-memory SQLite DB with all tables created.

    ``in_memory_engine`` already runs ``Base.metadata.create_all``; this fixture
    is a clarifying alias for orchestrator/CLI tests that need a real DB.
    """
    return db_session


@pytest.fixture
def mock_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    """Override settings for CLI tests to use a tmp SQLite DB and tmp raw_data_dir."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("GOVLINK_RAW_DATA_DIR", str(tmp_path / "raw"))
    from govlink.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()
