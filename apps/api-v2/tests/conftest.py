"""Opt-in PostgreSQL sessions isolated by an outer rollback transaction."""

import os
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool


@pytest_asyncio.fixture
async def integration_session():
    url = os.environ.get("NOSHIRO_INTEGRATION_DATABASE_URL", "")
    if not url:
        pytest.skip("dedicated PostgreSQL integration database required")
    if not urlsplit(url).path.endswith("_test"):
        pytest.fail("Integration database name must end with _test.")
    engine = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://", 1), poolclass=NullPool
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection, join_transaction_mode="create_savepoint"
                ) as session:
                    yield session
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
