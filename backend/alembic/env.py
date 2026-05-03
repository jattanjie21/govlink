"""Alembic migration environment.

Loads all dataset model modules via :func:`govlink.core.registry.get_registry().auto_discover`
so ``Base.metadata`` knows about every registered table — including
per-dataset data tables — before autogenerate runs.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Side-effect imports: registers all known tables on Base.metadata.
import govlink.core.models  # noqa: F401
from alembic import context
from govlink.config import get_settings
from govlink.core.registry import get_registry
from govlink.db import Base

# Load every registered dataset's model module so Base.metadata is complete.
get_registry().auto_discover()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB needed)."""
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live DB connection)."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section, {})
    if settings.database_url is not None:
        configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
