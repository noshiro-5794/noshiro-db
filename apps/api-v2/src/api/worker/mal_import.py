"""Import one MAL anime through the write primitives.

The mapper is deliberately thin: it only decides which parts of the payload become names,
a description, artwork, a profile, facts and metrics. Everything it calls has already been
verified against the schema on its own.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

import api.worker.ingestion as ingestion_module
from api.worker import entities, facts, metrics, presentation, profiles, records

PROVIDER = "mal"
NAMESPACE = "anime"
RESOURCE_TYPE = "subject"
MAPPER = "mal.anime"
MAPPER_VERSION = "mal-importer-v1"
SCHEMA_VERSION = "mal-api-v2"

ROMANIZED = "romanized"
OFFICIAL = "official"
ORIGINAL = "original"
ALIAS = "alias"


def name_entries(item: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The names a MAL payload carries, in the order the old importer wrote them."""
    entries: list[tuple[str, str, str]] = []
    title = item.get("title")
    if isinstance(title, str):
        entries.append((title, "", ROMANIZED))
    alternative = item.get("alternative_titles")
    alternative = alternative if isinstance(alternative, dict) else {}
    english = alternative.get("en")
    if isinstance(english, str):
        entries.append((english, "en", OFFICIAL))
    japanese = alternative.get("ja")
    if isinstance(japanese, str):
        entries.append((japanese, "ja", ORIGINAL))
    for synonym in alternative.get("synonyms") or []:
        if isinstance(synonym, str):
            entries.append((synonym, "", ALIAS))
    return entries


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def fact_candidates(item: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    """Facts a MAL payload supports, as ``slug -> (value, value_type)``."""
    broadcast = _as_dict(item.get("broadcast"))
    season = _as_dict(item.get("start_season"))
    duration = item.get("average_episode_duration")
    minutes = (
        max(1, round(int(duration) / 60))
        if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0
        else None
    )
    raw: dict[str, Any] = {
        "mal-status": item.get("status"),
        "mal-type": item.get("media_type"),
        "mal-season": season.get("season"),
        "mal-year": season.get("year"),
        "mal-score": item.get("mean"),
        "mal-rank": item.get("rank"),
        "mal-popularity": item.get("popularity"),
        "mal-members": item.get("num_list_users"),
        "episode-count": item.get("num_episodes"),
        "duration-minutes": minutes,
        "broadcast-day": broadcast.get("day_of_the_week"),
        "broadcast-time": broadcast.get("start_time"),
        "broadcast-timezone": "Asia/Tokyo" if broadcast else None,
    }
    out: dict[str, tuple[Any, str]] = {}
    for slug, value in raw.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int | float):
            value_type = "number"
        else:
            value_type = "string"
        out[slug] = (value, value_type)
    premiered = profiles.parse_iso_date(item.get("start_date"))
    if premiered is not None:
        out["release-date"] = (premiered.isoformat(), "date")
    ended = profiles.parse_iso_date(item.get("end_date"))
    if ended is not None:
        out["end-date"] = (ended.isoformat(), "date")
    return out


async def import_anime(session: AsyncSession, item: dict[str, Any]) -> Any:
    """Write one MAL anime, returning the canonical entity id."""
    external_id = str(item["id"])
    written = await records.record_payload(
        session,
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        resource_type=RESOURCE_TYPE,
        external_id=external_id,
        payload=item,
        schema_version=SCHEMA_VERSION,
        canonical_url=f"https://myanimelist.net/anime/{external_id}",
    )
    observation_id = await ingestion_module.record_observation(
        session,
        provider_record_id=written.record_id,
        mapper=MAPPER,
        mapper_version=MAPPER_VERSION,
        normalized_data=item,
        schema_name="index.work",
        schema_version="1",
    )
    mapped = await entities.map_work(
        session,
        provider_record_id=written.record_id,
        mapped_data={"subject_type": "anime", "nsfw": False},
    )
    await presentation.add_names(
        session,
        entity_id=mapped.entity_id,
        provider_record_id=written.record_id,
        observation_id=observation_id,
        entries=name_entries(item),
    )
    synopsis = item.get("synopsis")
    if isinstance(synopsis, str) and synopsis.strip():
        await presentation.upsert_description(
            session,
            entity_id=mapped.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            text=synopsis,
        )
    picture = _as_dict(item.get("main_picture"))
    large = picture.get("large")
    medium = picture.get("medium")
    poster = large if isinstance(large, str) and large else medium
    thumbnail = medium if isinstance(medium, str) and medium else large
    if isinstance(poster, str) or isinstance(thumbnail, str):
        await presentation.upsert_media(
            session,
            entity_id=mapped.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            original=poster if isinstance(poster, str) else "",
            thumbnail=thumbnail if isinstance(thumbnail, str) else "",
        )
    await profiles.upsert_anime_profile(
        session,
        work_entity_id=mapped.work_id,
        media_format=str(item.get("media_type") or "").upper(),
        episode_count=item.get("num_episodes")
        if isinstance(item.get("num_episodes"), int)
        else None,
        premiered_on=profiles.parse_iso_date(item.get("start_date")),
        ended_on=profiles.parse_iso_date(item.get("end_date")),
    )
    await profiles.upsert_external_link(
        session,
        entity_id=mapped.entity_id,
        provider_record_id=written.record_id,
        observation_id=observation_id,
        url=f"https://myanimelist.net/anime/{external_id}",
        label="MAL",
    )
    await metrics.record_metrics(
        session,
        entity_id=mapped.entity_id,
        provider_record_id=written.record_id,
        observed_at=await ingestion_module.observed_at(session, observation_id),
        values={
            "members": item.get("num_list_users"),
            "scoring-users": item.get("num_scoring_users"),
            "score": item.get("mean"),
        },
    )
    for slug, (value, value_type) in fact_candidates(item).items():
        await facts.record_fact(
            session,
            entity_id=mapped.entity_id,
            observation_id=observation_id,
            slug=slug,
            name=slug.replace("-", " ").title(),
            value=value,
            value_type=value_type,
            json_pointer=f"/{slug}",
        )
    await presentation.ensure_membership(session, entity_id=mapped.entity_id, work_type="anime")
    return mapped.entity_id


__all__ = [
    "MAPPER",
    "MAPPER_VERSION",
    "fact_candidates",
    "import_anime",
    "name_entries",
]
