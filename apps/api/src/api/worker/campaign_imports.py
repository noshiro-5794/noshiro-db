"""Fetch campaign items before entering their projection/acknowledgement transaction."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.integrations.providers.anilist import AniListClient
from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.mal import MALClient
from api.integrations.providers.vndb import VNDBClient
from api.worker import anilist_import, bangumi_sync, mal_import, vndb_import
from api.worker.source_fetches import archive_responses


async def fetch_source(
    provider: str,
    external_id: str,
    *,
    forbidden: bool,
    progress: Callable[[str, int | None], Awaitable[None]],
) -> Any:
    with archive_responses():
        if provider == "bangumi":
            bangumi = BangumiClient()
            bangumi.forbid_storage(forbidden=forbidden)
            try:
                return await bangumi_sync.fetch_batch(bangumi, int(external_id), progress=progress)
            finally:
                bangumi.close()
        if provider == "vndb":
            vndb = VNDBClient()
            vndb.forbid_storage(forbidden=forbidden)
            try:
                return await asyncio.to_thread(
                    vndb.fetch_import_batch, external_id, include_related=True
                )
            finally:
                vndb.close()
        if provider == "anilist":
            anilist = AniListClient()
            anilist.forbid_storage(forbidden=forbidden)
            try:
                return await asyncio.to_thread(anilist.fetch_media, int(external_id))
            finally:
                anilist.close()
        if provider == "mal":
            mal = MALClient()
            mal.forbid_storage(forbidden=forbidden)
            try:
                return await asyncio.to_thread(mal.fetch_anime, int(external_id))
            finally:
                mal.close()
        raise ValueError(f"Unsupported campaign provider: {provider}")


async def project_source(
    session: AsyncSession, provider: str, external_id: str, payload: Any
) -> Any:
    if provider == "bangumi":
        result = await bangumi_sync.project_batch(session, int(external_id), payload)
        return result["subject_id"]
    if provider == "vndb":
        return await vndb_import.import_batch(session, external_id, payload)
    if provider == "anilist":
        return await anilist_import.import_media(session, payload)
    if provider == "mal":
        return await mal_import.import_anime(session, payload)
    raise ValueError(f"Unsupported campaign provider: {provider}")
