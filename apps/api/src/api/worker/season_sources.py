"""Season listing capture with network requests outside database transactions."""

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import observations as ingestion
from api.contexts.ingestion import records
from api.db import fetch
from api.integrations.providers.anilist import AniListClient
from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.mal import MALClient, season_name_for_quarter
from api.worker import calendar_sync, snapshot_retention
from api.worker.session import session_scope
from api.worker.source_fetches import fetch_archived


def local_today() -> date:
    return datetime.now(ZoneInfo(os.environ.get("DEPLOYMENT_TIME_ZONE") or "Asia/Shanghai")).date()


async def prefetch_bangumi() -> dict[str, Any]:
    forbidden = await storage_forbidden("bangumi")
    client = BangumiClient()
    client.forbid_storage(forbidden=forbidden)
    try:
        data = await fetch_archived(session_scope, client.fetch_calendar)
    finally:
        client.close()
    if not isinstance(data, list):
        raise calendar_sync.CalendarError("Bangumi calendar response must be a list.")
    async with session_scope() as session:
        observation = await calendar_sync.record_calendar(session, data, datetime.now(UTC))
    return {"observation_id": str(observation), "weekday_count": len(data)}


def within_airing_horizon(media: dict[str, Any], today: date) -> bool:
    if str(media.get("status") or "").upper() == "RELEASING":
        return True
    start = media.get("startDate") or {}
    if not isinstance(start, dict):
        return False
    try:
        started = date(int(start["year"]), int(start.get("month") or 1), int(start.get("day") or 1))
    except (KeyError, TypeError, ValueError):
        return False
    return today - timedelta(days=30) <= started <= today + timedelta(days=150)


def mal_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    result = []
    for wrapper in data:
        if isinstance(wrapper, dict):
            result.append(wrapper["node"] if isinstance(wrapper.get("node"), dict) else wrapper)
    return result


def normalized_mal_item(item: dict[str, Any]) -> dict[str, Any]:
    raw_broadcast = item.get("broadcast")
    broadcast = raw_broadcast if isinstance(raw_broadcast, dict) else {}
    duration = item.get("average_episode_duration")
    return {
        "mal_id": item.get("id"),
        "media_type": item.get("media_type"),
        "status": item.get("status"),
        "start_date": item.get("start_date"),
        "broadcast_day": broadcast.get("day_of_the_week"),
        "broadcast_time": broadcast.get("start_time"),
        "timezone": "Asia/Tokyo" if broadcast else "",
        "duration_minutes": max(1, round(duration / 60))
        if isinstance(duration, int) and duration > 0
        else None,
    }


async def record_items(
    session: AsyncSession, provider: str, items: dict[str, dict[str, Any]], moment: datetime
) -> int:
    host = "myanimelist.net" if provider == "mal" else "anilist.co"
    for identifier, payload in items.items():
        await records.record_payload(
            session,
            provider_slug=provider,
            namespace_slug="schedule-item" if provider == "mal" else "season-item",
            resource_type="subject",
            external_id=identifier,
            payload=payload,
            canonical_url=f"https://{host}/anime/{identifier}",
            schema_version="mal-api-v2" if provider == "mal" else "anilist-graphql",
            fetched_at=moment,
        )
    return len(items)


async def storage_forbidden(provider: str) -> bool:
    async with session_scope() as session:
        rows = await fetch(
            session,
            "SELECT storage_policy FROM provider WHERE slug=:provider",
            {"provider": provider},
        )
        return bool(rows and rows[0].storage_policy == "forbidden")


async def sync_anilist(
    *,
    today: date | None = None,
    page_size: int = 50,
    max_pages: int = 40,
    airing: bool = True,
) -> dict[str, Any]:
    current = today or local_today()
    season = ("WINTER", "SPRING", "SUMMER", "FALL")[(current.month - 1) // 3]
    pages = []
    items = {}
    client = AniListClient()
    client.forbid_storage(forbidden=await storage_forbidden("anilist"))
    try:
        for number in range(1, max(1, max_pages) + 1):
            options: dict[str, Any] = {"cursor": str(number), "page_size": max(1, page_size)}
            if airing:
                page = await fetch_archived(session_scope, client.fetch_airing_page, **options)
            else:
                page = await fetch_archived(
                    session_scope,
                    client.fetch_season_page,
                    season=season,
                    season_year=current.year,
                    **options,
                )
            pages.append(page)
            for item in page.get("media") or []:
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("id"), int)
                    and (not airing or within_airing_horizon(item, current))
                ):
                    items[str(item["id"])] = item
            info = page.get("pageInfo") or {}
            if not isinstance(info, dict) or info.get("hasNextPage") is not True:
                break
    finally:
        client.close()
    moment = datetime.now(UTC)
    season_key = f"{season.lower()}:{current.year}"
    payload = {"season": season, "season_year": current.year, "pages": pages}
    if airing:
        payload["mode"] = "airing"
    mapper = "anilist.airing-list" if airing else "anilist.season-now"
    version = "anilist-airing-list-v1" if airing else "anilist-season-v1"
    async with session_scope() as session:
        written = await records.record_payload(
            session,
            provider_slug="anilist",
            namespace_slug="season",
            resource_type="schedule",
            external_id="airing:current" if airing else f"season:{season_key}",
            payload=payload,
            canonical_url="https://anilist.co/browse/anime",
            schema_version="anilist-graphql",
            fetched_at=moment,
        )
        await ingestion.record_observation(
            session,
            provider_record_id=written.record_id,
            mapper=mapper,
            mapper_version=version,
            normalized_data=payload,
            schema_name="index.schedule",
            schema_version="1",
            observed_at=moment,
        )
        await snapshot_retention.retain_current(session, written.record_id)
        recorded = await record_items(session, "anilist", items, moment)
    result = {
        "season_key": season_key,
        "pages": len(pages),
        "season_record_id": str(written.record_id),
        "changed": written.changed,
        "items_seen": len(items),
        "items_recorded": recorded,
    }
    if airing:
        result["mode"] = "airing"
    return result


async def sync_mal(
    *, today: date | None = None, limit: int = 500, max_pages: int = 10
) -> dict[str, Any]:
    current = today or local_today()
    quarter = (current.month - 1) // 3 + 1
    season = season_name_for_quarter(quarter)
    season_key = f"{current.year}Q{quarter}"
    pages = []
    items = {}
    offset = 0
    client = MALClient()
    client.forbid_storage(forbidden=await storage_forbidden("mal"))
    try:
        for _ in range(max(1, max_pages)):
            payload = await fetch_archived(
                session_scope,
                client.fetch_season,
                year=current.year,
                season=season,
                offset=offset,
                limit=max(1, limit),
            )
            pages.append(payload)
            nodes = mal_nodes(payload)
            for node in nodes:
                if isinstance(node.get("id"), int):
                    items[str(node["id"])] = node
            paging = payload.get("paging")
            if not nodes or not isinstance(paging, dict) or not paging.get("next"):
                break
            offset += len(nodes)
    finally:
        client.close()
    moment = datetime.now(UTC)
    async with session_scope() as session:
        written = await records.record_payload(
            session,
            provider_slug="mal",
            namespace_slug="season",
            resource_type="schedule",
            external_id=f"season-now:{season_key}",
            payload={
                "season_key": season_key,
                "year": current.year,
                "season": season,
                "pages": pages,
            },
            canonical_url=f"https://api.myanimelist.net/v2/anime/season/{current.year}/{season}",
            schema_version="mal-api-v2",
            fetched_at=moment,
        )
        await ingestion.record_observation(
            session,
            provider_record_id=written.record_id,
            mapper="mal.season",
            mapper_version="mal-season-v2",
            normalized_data={
                "season_key": season_key,
                "year": current.year,
                "season": season,
                "items": [normalized_mal_item(item) for item in items.values()],
            },
            schema_name="index.schedule",
            schema_version="2",
            observed_at=moment,
        )
        await snapshot_retention.retain_current(session, written.record_id)
        recorded = await record_items(session, "mal", items, moment)
    return {
        "source": "mal",
        "season": {
            "season_key": season_key,
            "mal_season": season,
            "pages": len(pages),
            "schedule_record_id": str(written.record_id),
            "changed": written.changed,
            "items_seen": len(items),
            "items_recorded": recorded,
        },
        "fetched_at": moment.isoformat(),
    }
