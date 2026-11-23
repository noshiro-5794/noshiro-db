"""Atomic AniList media projection, including source metadata and related graph."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.names import SourceName
from api.contexts.index import resolution
from api.contexts.ingestion import entities, facts, metrics, profiles, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import observations as ingestion
from api.db import fetch
from api.shared.text import slugify

PROVIDER = "anilist"
NAMESPACE = "anime"
RESOURCE_TYPE = "subject"
MAPPER = "anilist.media"
MAPPER_VERSION = "anilist-media-v2"
SCHEMA_VERSION = "anilist-graphql"

FACT_POINTERS = {
    "anilist-status": "/status",
    "anilist-season": "/season",
    "anilist-season-year": "/seasonYear",
    "episode-count": "/episodes",
    "duration-minutes": "/duration",
    "anilist-source": "/source",
    "release-date": "/startDate",
    "end-date": "/endDate",
    "anilist-id-mal": "/idMal",
    "anilist-trending": "/trending",
}


def as_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _fuzzy_date(block: Any) -> str | None:
    if not isinstance(block, dict):
        return None
    year, month, day = block.get("year"), block.get("month"), block.get("day")
    if not isinstance(year, int) or not isinstance(month, int):
        return None
    if not isinstance(day, int):
        day = 1
    try:
        return datetime(year, month, day, tzinfo=UTC).date().isoformat()
    except ValueError:
        return None


def name_entries(media: dict[str, Any]) -> list[SourceName]:
    title = media.get("title") or {}
    entries = []
    for key, kind in (
        ("romaji", "romanized"),
        ("english", "official"),
        ("native", "original"),
        ("userPreferred", "official"),
    ):
        value = title.get(key)
        if isinstance(value, str) and value:
            entries.append(
                SourceName(
                    value[:256],
                    "ja" if key in {"native", "romaji"} else "en",
                    kind,
                    is_official=True,
                    script="Jpan" if key == "native" else "Latn",
                )
            )
    entries.extend(
        SourceName(value[:256], "", "alias")
        for value in media.get("synonyms") or []
        if isinstance(value, str) and value
    )
    return entries


def fact_candidates(media: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    values = {
        "anilist-status": media.get("status"),
        "anilist-season": media.get("season"),
        "anilist-season-year": media.get("seasonYear"),
        "episode-count": as_int(media.get("episodes")),
        "duration-minutes": as_int(media.get("duration")),
        "anilist-source": media.get("source"),
        "release-date": _fuzzy_date(media.get("startDate")),
        "end-date": _fuzzy_date(media.get("endDate")),
        "anilist-id-mal": as_int(media.get("idMal")),
        "anilist-trending": media.get("trending"),
    }
    result = {}
    for slug, value in values.items():
        if value is None or value == "":
            continue
        value_type = "date" if slug in {"release-date", "end-date"} else "string"
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int | Decimal):
            value_type = "number"
        result[slug] = (value, value_type)
    return result


async def import_saved_media(session: AsyncSession, anilist_id: int) -> Any:
    rows = await fetch(
        session,
        """
        SELECT revision.payload FROM provider_record AS r
        JOIN provider_namespace AS n ON n.id=r.namespace_id
        JOIN provider AS p ON p.id=n.provider_id
        JOIN provider_revision AS revision ON revision.id=r.latest_revision_id
        WHERE p.slug='anilist' AND n.slug='season-item' AND r.external_id=:id AND r.status='active'
        """,
        {"id": str(anilist_id)},
    )
    if not rows:
        raise ValueError(f"AniList media {anilist_id} has no persisted seasonal payload.")
    payload = rows[0].payload
    if not isinstance(payload, dict) or payload.get("id") != anilist_id:
        raise ValueError(f"AniList media {anilist_id} payload is inconsistent.")
    return await import_media(session, payload)


async def _retire_partial_mapper(session: AsyncSession, record_id: Any) -> None:
    fields = await fetch(
        session,
        """
        SELECT DISTINCT f.entity_id, f.predicate_id, f.language
        FROM provider_current_observation AS c
        JOIN fact_evidence AS e ON e.observation_id=c.observation_id
        JOIN fact AS f ON f.id=e.fact_id
        WHERE c.provider_record_id=:record AND c.mapper='anilist.anime'
          AND c.schema_name='index.work'
        """,
        {"record": record_id},
    )
    await fetch(
        session,
        "DELETE FROM provider_current_observation WHERE provider_record_id=:record"
        " AND mapper='anilist.anime' AND schema_name='index.work' RETURNING id",
        {"record": record_id},
    )
    for field in fields:
        await resolution.rebuild_fact(
            session,
            entity_id=field.entity_id,
            predicate_id=field.predicate_id,
            language=field.language,
        )


async def import_media(session: AsyncSession, media: dict[str, Any]) -> Any:
    from api.worker import anilist_airing, anilist_graph

    async with session.begin_nested():
        external_id = str(media["id"])
        upstream = media.get("updatedAt")
        written = await records.record_payload(
            session,
            provider_slug=PROVIDER,
            namespace_slug=NAMESPACE,
            resource_type=RESOURCE_TYPE,
            external_id=external_id,
            payload=media,
            schema_version=SCHEMA_VERSION,
            canonical_url=media.get("siteUrl") or f"https://anilist.co/anime/{external_id}",
            upstream_updated_at=datetime.fromtimestamp(upstream, tz=UTC)
            if isinstance(upstream, int) and upstream > 0
            else None,
        )
        observation_id = await ingestion.record_observation(
            session,
            provider_record_id=written.record_id,
            mapper=MAPPER,
            mapper_version=MAPPER_VERSION,
            normalized_data=media,
            schema_name="index.work",
            schema_version="1",
        )
        await _retire_partial_mapper(session, written.record_id)
        entity = await entities.map_work(
            session,
            provider_record_id=written.record_id,
            mapped_data={"subject_type": "anime", "nsfw": media.get("isAdult") is True},
        )
        await presentation.record_names(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            entries=name_entries(media),
        )
        description = media.get("description")
        if isinstance(description, str) and description.strip():
            await presentation.upsert_description(
                session,
                entity_id=entity.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                text=description,
            )
        cover = media.get("coverImage") or {}
        await presentation.upsert_media(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            original=cover.get("large") or "",
            thumbnail=cover.get("medium") or "",
        )
        banner = media.get("bannerImage")
        if isinstance(banner, str) and banner:
            await presentation.upsert_media(
                session,
                entity_id=entity.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                original=banner,
            )
        await profiles.upsert_anime_profile(
            session,
            work_entity_id=entity.work_id,
            media_format=media.get("format") or "",
            episode_count=as_int(media.get("episodes")),
            source_material=media.get("source") or "",
            premiered_on=profiles.parse_iso_date(_fuzzy_date(media.get("startDate"))),
            ended_on=profiles.parse_iso_date(_fuzzy_date(media.get("endDate"))),
            replace_metadata=True,
        )
        links = [
            {"url": media.get("siteUrl"), "site": "AniList"},
            *(media.get("externalLinks") or []),
        ]
        for item in links:
            if isinstance(item, dict):
                url = item.get("url")
                label = item.get("site") or ""
            else:
                url = item
                label = ""
            if not isinstance(url, str) or not url:
                continue
            await profiles.upsert_external_link(
                session,
                entity_id=entity.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                url=url,
                label=label[:128],
                link_type=slugify(label)[:64],
            )
        for slug, (value, value_type) in fact_candidates(media).items():
            await facts.record_fact(
                session,
                entity_id=entity.entity_id,
                observation_id=observation_id,
                slug=slug,
                name=slug.replace("-", " ").title(),
                value=value,
                value_type=value_type,
                json_pointer=FACT_POINTERS[slug],
            )
        await metrics.record_metrics(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observed_at=await ingestion.observed_at(session, observation_id),
            values={
                "popularity": media.get("popularity"),
                "favourites": media.get("favourites"),
                "trending": media.get("trending"),
                "score": media.get("averageScore"),
            },
        )
        await presentation.ensure_membership(
            session,
            entity_id=entity.entity_id,
            work_type="anime",
            inclusion_reason="AniList anime",
        )
        await anilist_graph.import_graph(session, entity.entity_id, observation_id, media)
        await anilist_airing.import_schedule(session, entity.entity_id, media)
        return await resolution.resolve(session, entity.entity_id)
