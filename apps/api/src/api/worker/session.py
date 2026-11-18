"""One session per task, committed only when the work finished.

The engine is created **per task**, not once per process. A Celery task runs its coroutine
through `asyncio.run`, which builds a fresh event loop each time; an asyncpg connection
pooled by a previous loop cannot be used by the next one, and reusing the engine fails with
"attached to a different loop" on the second task. `NullPool` makes that explicit: no
connection outlives the loop it was opened in.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import settings


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        settings.async_database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()
