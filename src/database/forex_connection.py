from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.core.config import FOREX_DATABASE_URL

# Initialize Async Engine for Forex Service
engine_forex: AsyncEngine = create_async_engine(
    FOREX_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

# Create Session Factory for Async Sessions
SessionForex: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine_forex,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

BaseForex = declarative_base()


async def get_forex_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for providing async DB sessions per request."""
    async with SessionForex() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_forex_session_factory() -> async_sessionmaker[AsyncSession]:
    """Helper for background tasks / workers to create independent async sessions."""
    return SessionForex
