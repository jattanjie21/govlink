"""Pytest configuration and shared fixtures.

Shared fixtures for database sessions, FastAPI test client,
sample PDFs, and registry isolation live here.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

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
