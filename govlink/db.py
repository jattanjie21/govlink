"""Database engine and session management.

Constructs the SQLAlchemy engine from configuration, exposes a session
factory, declares the ORM ``Base`` class with a constraint naming
convention, and provides a FastAPI-compatible session dependency.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for every govlink ORM model."""

    metadata = metadata


_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLite ``connect`` event listener that enables FK enforcement."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine_from_url(url: str, echo: bool = False) -> Engine:
    """Build a SQLAlchemy ``Engine`` with backend-appropriate tuning.

    SQLite URLs get ``StaticPool`` and ``check_same_thread=False`` so a
    single in-memory database is shared across threads in tests, plus a
    ``connect`` listener that enables ``PRAGMA foreign_keys=ON``. All
    other backends use SQLAlchemy's default pool with no overrides.
    """
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            echo=echo,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, echo=echo)


def init_db(database_url: str | None = None) -> None:
    """Initialise the module-level engine and session factory.

    If ``database_url`` is None, the URL is read from
    :func:`govlink.config.get_settings`. Re-calling this function rebuilds
    both ``_engine`` and ``SessionLocal``.
    """
    global _engine, SessionLocal

    if database_url is None:
        from govlink.config import get_settings

        database_url = get_settings().database_url
        if database_url is None:
            raise RuntimeError("database_url not configured")

    _engine = create_engine_from_url(database_url)
    SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)


def get_engine() -> Engine:
    """Return the initialised engine; raise if ``init_db`` was never called."""
    if _engine is None:
        raise RuntimeError("Database not initialised — call init_db() first.")
    return _engine


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a ``Session`` and closing it afterwards."""
    if SessionLocal is None:
        init_db()
    assert SessionLocal is not None  # for mypy
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
