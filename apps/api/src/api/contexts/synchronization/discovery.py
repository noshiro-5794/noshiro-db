"""Discovery adapters combining provider cursors with durable local frontiers."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch
from api.integrations.providers.anilist import AniListClient
from api.integrations.providers.catalog import CatalogPage, DeltaPage
from api.integrations.providers.vndb import VNDBClient
from api.worker.frontier import highest_stored_id, read_frontier


async def numeric_page(
    session: AsyncSession, provider: str, cursor: str | None, page_size: int
) -> CatalogPage:
    namespace = "anime" if provider == "mal" else "subject"
    floor = int(os.environ.get("MAL_MAX_ANIME_ID", "65500")) if provider == "mal" else 0
    seed = max(
        floor, await highest_stored_id(session, provider_slug=provider, namespace_slug=namespace)
    )
    frontier = await read_frontier(
        session, provider_slug=provider, namespace_slug=namespace, seed=seed
    )
    start = max(1, int(cursor or "1"))
    end = min(frontier.ceiling, start + max(1, page_size) - 1)
    ids = tuple(str(value) for value in range(start, end + 1))
    return CatalogPage(
        ids, str(end + 1) if end < frontier.ceiling else None, total_count=frontier.ceiling
    )


async def bangumi_reconciliation(
    session: AsyncSession, cursor: str | None, page_size: int
) -> DeltaPage:
    offset = max(0, int(cursor or "0"))
    limit = min(max(page_size, 1), 1000)
    base = """
        FROM provider_record r JOIN provider_namespace ns ON ns.id = r.namespace_id
        JOIN provider p ON p.id = ns.provider_id
        WHERE p.slug = 'bangumi' AND ns.slug = 'subject' AND r.status = 'active'
    """
    rows = await fetch(
        session,
        "SELECT r.external_id " + base + " ORDER BY r.external_id LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset},
    )
    count = await fetch(session, "SELECT count(*) AS total " + base, {})
    ids = tuple(row.external_id for row in rows)
    return DeltaPage(
        ids,
        str(offset + limit) if len(ids) == limit else None,
        "known-record-reconciliation",
        total_count=int(count[0].total),
    )


async def highest_vndb_id(session: AsyncSession) -> int:
    rows = await fetch(
        session,
        """
        SELECT max(CAST(regexp_replace(r.external_id, '^[vV]+', '') AS numeric)) AS highest
        FROM provider_record r JOIN provider_namespace ns ON ns.id = r.namespace_id
        JOIN provider p ON p.id = ns.provider_id
        WHERE p.slug = 'vndb' AND ns.slug = 'vn' AND r.external_id ~ '^[vV]*[0-9]+$'
    """,
        {},
    )
    return int(rows[0].highest or 0)


async def discover_page(
    session: AsyncSession,
    provider: str,
    *,
    cursor: str | None = None,
    page_size: int = 100,
    watermark: str | None = None,
) -> CatalogPage | DeltaPage:
    if provider not in {"bangumi", "mal", "vndb", "anilist"}:
        raise ValueError(f"Unsupported campaign provider: {provider}")
    if provider == "bangumi" and watermark is not None:
        return await bangumi_reconciliation(session, cursor, page_size)
    if provider in {"bangumi", "mal"}:
        return await numeric_page(session, provider, cursor, page_size)
    policy = await fetch(
        session,
        "SELECT storage_policy FROM provider WHERE slug = :provider",
        {"provider": provider},
    )
    forbidden = bool(policy and policy[0].storage_policy == "forbidden")
    if provider == "anilist":
        anilist = AniListClient()
        anilist.forbid_storage(forbidden=forbidden)
        try:
            if watermark is None:
                return await asyncio.to_thread(
                    anilist.discover_anime_page, cursor=cursor, page_size=page_size
                )
            return await asyncio.to_thread(
                anilist.discover_anime_delta_page,
                watermark=watermark,
                cursor=cursor,
                page_size=page_size,
            )
        finally:
            anilist.close()
    vndb = VNDBClient()
    vndb.forbid_storage(forbidden=forbidden)
    try:
        if watermark is None:
            return await asyncio.to_thread(
                vndb.discover_vn_page, cursor=cursor, page_size=page_size
            )
        seed = (
            await highest_vndb_id(session) if not watermark.isdigit() or int(watermark) <= 0 else 0
        )
        return await asyncio.to_thread(
            vndb.discover_vn_delta_page,
            watermark=watermark,
            cursor=cursor,
            page_size=page_size,
            seed=seed,
        )
    finally:
        vndb.close()
