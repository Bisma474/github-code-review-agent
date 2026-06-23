from contextlib import asynccontextmanager
from logging import getLogger
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
import app.db.models  # noqa: F401 — registers all models with Base.metadata
from app.core.config import get_settings

logger = getLogger(__name__)
settings = get_settings()


def create_db_engine() -> AsyncEngine:
    """
    Create async database engine from DATABASE_URL.

    Supports both PostgreSQL (postgresql+asyncpg://) and SQLite (sqlite+aiosqlite://).
    """
    logger.info(f"Creating database engine with URL: {settings.DATABASE_URL}")

    kwargs = {"echo": settings.LOG_LEVEL == "DEBUG"}
    if "sqlite" not in settings.DATABASE_URL:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    url = settings.DATABASE_URL
    if "sslmode=require" in url:
        url = url.split("?")[0]
        kwargs["connect_args"] = {"ssl": "require"}

    engine = create_async_engine(url, **kwargs)

    return engine


engine = create_db_engine()

logger.info("Database engine created successfully")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Yields a session, commits on success, rolls back on exception.
    Must be used as a context manager.
    """
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise


async def get_db():
    """
    Async database session context manager (deprecated, use get_async_session).
    Kept for backward compatibility.
    """
    async with get_async_session() as session:
        yield session


async def create_tables() -> None:
    """
    Create all tables in the database.
    """
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def drop_tables() -> None:
    """
    Drop all tables in the database.
    Use with caution - this will delete all data.
    """
    logger.warning("Dropping all database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped")