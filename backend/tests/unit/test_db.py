"""Tests for govlink.db — engine factory, session factory, declarative base."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import govlink.db as db_module
from govlink.db import (
    Base,
    create_engine_from_url,
    get_engine,
    get_session,
    init_db,
)


def test_create_engine_with_sqlite_url_uses_static_pool() -> None:
    """SQLite URLs must use ``StaticPool`` and ``check_same_thread=False``."""
    engine = create_engine_from_url("sqlite:///:memory:")
    assert isinstance(engine.pool, StaticPool)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_create_engine_with_postgres_url_uses_default_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-SQLite URLs must NOT receive StaticPool or check_same_thread overrides.

    A real Postgres engine cannot be constructed in-process without a driver
    installed, so we monkey-patch ``sqlalchemy.create_engine`` and assert
    that our factory routes Postgres URLs through the default-pool branch
    (i.e. no ``poolclass`` and no ``connect_args``).
    """
    captured: dict[str, Any] = {}

    def fake_create_engine(url: Any, **kwargs: Any) -> Any:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock(spec=Engine)

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)
    create_engine_from_url("postgresql+psycopg://u:p@localhost:5432/db")
    assert captured["url"] == "postgresql+psycopg://u:p@localhost:5432/db"
    assert "poolclass" not in captured["kwargs"]
    assert "connect_args" not in captured["kwargs"]


def test_create_engine_normalises_bare_postgresql_url_to_psycopg_v3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``postgresql://`` URLs (e.g. from Railway/Heroku) must be pinned to psycopg v3.

    SQLAlchemy resolves the bare scheme to the legacy ``psycopg2`` driver,
    which we do not ship; we depend on ``psycopg[binary]`` (v3) instead.
    """
    captured: dict[str, Any] = {}

    def fake_create_engine(url: Any, **kwargs: Any) -> Any:
        captured["url"] = url
        return MagicMock(spec=Engine)

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)
    create_engine_from_url("postgresql://u:p@host:5432/db")
    assert captured["url"] == "postgresql+psycopg://u:p@host:5432/db"


def test_create_engine_normalises_legacy_postgres_url_to_psycopg_v3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``postgres://`` (Heroku-style legacy form) must also be pinned to psycopg v3."""
    captured: dict[str, Any] = {}

    def fake_create_engine(url: Any, **kwargs: Any) -> Any:
        captured["url"] = url
        return MagicMock(spec=Engine)

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)
    create_engine_from_url("postgres://u:p@host:5432/db")
    assert captured["url"] == "postgresql+psycopg://u:p@host:5432/db"


def test_create_engine_preserves_explicit_postgres_driver_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit ``postgresql+<driver>://`` URLs must not be rewritten."""
    captured: dict[str, Any] = {}

    def fake_create_engine(url: Any, **kwargs: Any) -> Any:
        captured["url"] = url
        return MagicMock(spec=Engine)

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)
    create_engine_from_url("postgresql+psycopg2://u:p@host:5432/db")
    assert captured["url"] == "postgresql+psycopg2://u:p@host:5432/db"


def test_create_engine_enables_sqlite_foreign_keys(tmp_path: Path) -> None:
    """SQLite engines must enforce ``PRAGMA foreign_keys=ON`` on every connection."""
    db_path = tmp_path / "fk.db"
    engine = create_engine_from_url(f"sqlite:///{db_path}")

    md = MetaData()
    Table("parent", md, Column("id", Integer, primary_key=True))
    child = Table(
        "child",
        md,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("parent.id"), nullable=False),
    )
    md.create_all(engine)

    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(child.insert().values(id=1, parent_id=999))


def test_session_factory_yields_session(tmp_path: Path) -> None:
    """``init_db`` must wire up a ``SessionLocal`` that yields usable sessions."""
    db_path = tmp_path / "session.db"
    init_db(f"sqlite:///{db_path}")
    from govlink.db import SessionLocal

    assert SessionLocal is not None
    with SessionLocal() as session:
        assert isinstance(session, Session)
        assert session.execute(text("SELECT 1")).scalar() == 1


def test_get_session_dependency_closes_session_after_use(tmp_path: Path) -> None:
    """The ``get_session`` generator must close its session after yielding.

    SQLAlchemy's ``Session.is_active`` does not flip on close, so we instead
    perform an operation (which opens an implicit transaction) and assert
    that ``in_transaction()`` returns False once the generator exhausts —
    proof that ``session.close()`` ran in the ``finally`` block.
    """
    db_path = tmp_path / "dep.db"
    init_db(f"sqlite:///{db_path}")
    gen = get_session()
    session = next(gen)
    session.execute(text("SELECT 1"))
    assert session.in_transaction()
    with pytest.raises(StopIteration):
        gen.send(None)
    assert not session.in_transaction()


def test_get_session_closes_session_on_exception(tmp_path: Path) -> None:
    """The dependency must still close the session if the consumer raises."""
    db_path = tmp_path / "dep-exc.db"
    init_db(f"sqlite:///{db_path}")
    gen = get_session()
    session = next(gen)
    session.execute(text("SELECT 1"))
    assert session.in_transaction()
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert not session.in_transaction()


def test_base_class_has_expected_metadata() -> None:
    """``Base.metadata`` must be a SQLAlchemy ``MetaData`` instance with naming convention."""
    assert isinstance(Base.metadata, MetaData)
    nc = Base.metadata.naming_convention
    assert nc["pk"] == "pk_%(table_name)s"
    assert "ix" in nc
    assert "fk" in nc


def test_get_engine_raises_before_init_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_engine`` must raise if ``init_db`` has not been called."""
    import govlink.db as db_module

    monkeypatch.setattr(db_module, "_engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)
    with pytest.raises(RuntimeError):
        get_engine()


def test_init_db_uses_settings_when_no_url_provided(
    settings_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``init_db()`` with no argument must read ``database_url`` from settings."""
    db_path = tmp_path / "from-settings.db"
    settings_env.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    init_db()
    engine = get_engine()
    assert isinstance(engine, Engine)
    assert str(db_path) in str(engine.url)


def test_init_db_is_idempotent_replaces_engine(tmp_path: Path) -> None:
    """Re-calling ``init_db`` must rebuild the engine and SessionLocal."""
    init_db(f"sqlite:///{tmp_path / 'a.db'}")
    first = get_engine()
    init_db(f"sqlite:///{tmp_path / 'b.db'}")
    second = get_engine()
    assert first is not second


def test_init_db_raises_when_settings_database_url_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``init_db()`` must raise if Settings yields a ``None`` database_url."""

    class _StubSettings:
        database_url = None

    def _fake_get_settings() -> _StubSettings:
        return _StubSettings()

    import govlink.config as config_module

    monkeypatch.setattr(config_module, "get_settings", _fake_get_settings)
    with pytest.raises(RuntimeError, match="database_url not configured"):
        init_db()


def test_get_session_lazy_inits_when_session_local_is_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``get_session()`` must auto-call ``init_db`` when SessionLocal is None."""
    monkeypatch.setattr(db_module, "_engine", None)
    monkeypatch.setattr(db_module, "SessionLocal", None)

    db_path = tmp_path / "lazy.db"
    monkeypatch.setenv("GOVLINK_DATABASE_URL", f"sqlite:///{db_path}")
    from govlink.config import get_settings

    get_settings.cache_clear()

    gen = get_session()
    session = next(gen)
    assert session.execute(text("SELECT 1")).scalar() == 1
    with pytest.raises(StopIteration):
        gen.send(None)
    get_settings.cache_clear()
