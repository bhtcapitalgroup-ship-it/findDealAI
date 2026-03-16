"""
Alembic environment configuration for RealDeal AI.

Configured for async SQLAlchemy with PostgreSQL.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import your models' Base metadata so Alembic can detect schema changes.
# All models must be imported before this line for autogenerate to work.
from app.models.base import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.property import Property  # noqa: F401
from app.models.saved_deal import SavedDeal  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.market_data import MarketData  # noqa: F401

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Set up Python logging from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if available
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Ensure we use the asyncpg driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for generating migration SQL to review or apply manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using a synchronous connection (called within async context)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include object names for more readable migrations
        include_name=lambda name, type_, parent_names: True,
        # Render custom types (e.g., PostGIS Geography) correctly
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.

    Creates an async engine from the alembic configuration, acquires a
    connection, and delegates to do_run_migrations for the actual work.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — dispatches to the async runner."""
    asyncio.run(run_async_migrations())


# Determine execution mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
