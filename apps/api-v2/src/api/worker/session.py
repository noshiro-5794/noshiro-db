"""One session per task, committed only when the work finished."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings

# A worker process is long-lived and runs one task at a time per slot, so the pool can
# stay small; pre-ping covers the broker's idle reconnects.
_engine = create_async_engine(settings.async_database_url, pool_pre_ping=True, pool_size=2)
_sessions = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with _sessions() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
