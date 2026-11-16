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


@pytest_asyncio.fixture
async def register_provider(integration_session):
    from api.contexts.presentation.fragments import fetch

    async def register(slug, name):
        await fetch(
            integration_session,
            """
            INSERT INTO provider
              (slug, name, base_url, terms_url, attribution_url, license_name,
               storage_policy, redistribution_policy, commercial_use_policy,
               ai_usage_policy, is_enabled, created_at, updated_at)
            VALUES (:slug, :name, '', '', '', '', 'allowed', 'unknown', 'unknown',
                    'unknown', true, now(), now())
            ON CONFLICT (slug) DO NOTHING RETURNING id
            """,
            {"slug": slug, "name": name},
        )

    return register


@pytest_asyncio.fixture
async def vndb_session(integration_session, register_provider):
    await register_provider("vndb", "VNDB")
    return integration_session


@pytest_asyncio.fixture
async def mal_session(integration_session, register_provider):
    await register_provider("mal", "MyAnimeList")
    return integration_session


@pytest_asyncio.fixture
async def anilist_session(integration_session, register_provider):
    await register_provider("anilist", "AniList")
    return integration_session
