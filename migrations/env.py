import asyncio
import os
import pathlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.models import Base

target_metadata = Base.metadata


def _load_database_url() -> str:
    """Read DATABASE_URL from .env file or environment, normalising to asyncpg."""
    # Try environment first
    url = os.environ.get("DATABASE_URL", "")

    # Fall back to .env file
    if not url:
        dotenv = pathlib.Path(__file__).resolve().parent.parent / ".env"
        if dotenv.exists():
            for line in dotenv.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL") and "=" in line:
                    _, _, url = line.partition("=")
                    url = url.strip().strip('"').strip("'")
                    break

    if not url:
        raise RuntimeError("DATABASE_URL not set in environment or .env")

    # Alembic async runner needs postgresql+asyncpg:// scheme
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    url = _load_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = _load_database_url()

    # asyncpg does not accept sslmode in the URL — strip it and use connect_args
    connect_args = {}
    if "sslmode=require" in url:
        url = url.split("?")[0]
        connect_args["ssl"] = "require"

    connectable = create_async_engine(url, poolclass=NullPool, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
