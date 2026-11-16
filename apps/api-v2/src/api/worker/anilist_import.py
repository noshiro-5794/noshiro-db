"""Import one AniList media through the write primitives.

The fact that matters most here is ``anilist-id-mal``: it is AniList's own statement that
this work is MAL id *N*, and it is what the official-id reconciliation reads to bind the two
providers together. Without it that task can only abstain.

Not ported yet, named rather than skipped: characters, staff, studios, relations and the
per-provider metrics.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.worker import entities, facts, ingestion, presentation, profiles, records

PROVIDER = "anilist"
NAMESPACE = "anime"
RESOURCE_TYPE = "subject"
MAPPER = "anilist.anime"
MAPPER_VERSION = "anilist-importer-v1"
SCHEMA_VERSION = "anilist-graphql-v1"

ROMANIZED = "romanized"
OFFICIAL = "official"
ORIGINAL = "original"


def _title_block(media: dict[str, Any]) -> dict[str, Any]:
    title = media.get("title")
    return title if isinstance(title, dict) else {}


def name_entries(media: dict[str, Any]) -> list[tuple[str, str, str]]:
    title = _title_block(media)
    entries: list[tuple[str, str, str]] = []
    for key, language, kind in (
        ("romaji", "", ROMANIZED),
        ("english", "en", OFFICIAL),
        ("native", "ja", ORIGINAL),
    ):
        value = title.get(key)
        if isinstance(value, str) and value.strip():
            entries.append((value.strip()[:256], language, kind))
    return entries


def _fuzzy_date(block: Any) -> str | None:
    """AniList dates arrive as ``{year, month, day}`` with any part possibly null."""
    if not isinstance(block, dict):
        return None
    year, month, day = block.get("year"), block.get("month"), block.get("day")
    if not isinstance(year, int) or not isinstance(month, int):
        return None
    if not isinstance(day, int) or not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def fact_candidates(media: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    out: dict[str, tuple[Any, str]] = {}
    id_mal = media.get("idMal")
    if isinstance(id_mal, int) and not isinstance(id_mal, bool):
        out["anilist-id-mal"] = (id_mal, "number")
    raw: dict[str, Any] = {
        "anilist-format": media.get("format"),
        "anilist-status": media.get("status"),
        "anilist-season": media.get("season"),
        "anilist-season-year": media.get("seasonYear"),
        "anilist-score": media.get("averageScore"),
        "anilist-popularity": media.get("popularity"),
        "episode-count": media.get("episodes"),
        "duration-minutes": media.get("duration"),
    }
    for slug, value in raw.items():
        if value is None or value == "":
            continue
        out[slug] = (value, "number" if isinstance(value, int) else "string")
    started = _fuzzy_date(media.get("startDate"))
    if started:
        out["release-date"] = (started, "date")
    ended = _fuzzy_date(media.get("endDate"))
    if ended:
        out["end-date"] = (ended, "date")
    return out


def _cover(media: dict[str, Any]) -> tuple[str, str]:
    cover = media.get("coverImage")
    if not isinstance(cover, dict):
        return "", ""
    large = cover.get("large")
    medium = cover.get("medium")
    return (
        large if isinstance(large, str) else "",
        medium if isinstance(medium, str) else "",
    )


async def import_media(session: AsyncSession, media: dict[str, Any]) -> Any:
    """Write one AniList media, returning the canonical entity id."""
    external_id = str(media["id"])
    written = await records.record_payload(
        session,
        provider_slug=PROVIDER,
        namespace_slug=NAMESPACE,
        resource_type=RESOURCE_TYPE,
        external_id=external_id,
        payload=media,
        schema_version=SCHEMA_VERSION,
        canonical_url=f"https://anilist.co/anime/{external_id}",
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
    adult = (
        isinstance(media.get("description"), str)
        and "hentai" in str(media.get("genres") or []).lower()
    )
    entity = await entities.map_work(
        session,
        provider_record_id=written.record_id,
        mapped_data={"subject_type": "anime", "nsfw": adult},
    )
    entries = name_entries(media)
    if entries:
        await presentation.add_names(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            entries=entries,
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
    large, medium = _cover(media)
    if large or medium:
        await presentation.upsert_media(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            original=large,
            thumbnail=medium,
        )
    await profiles.upsert_anime_profile(
        session,
        work_entity_id=entity.work_id,
        media_format=str(media.get("format") or "").upper(),
        episode_count=media.get("episodes") if isinstance(media.get("episodes"), int) else None,
        premiered_on=profiles.parse_iso_date(_fuzzy_date(media.get("startDate"))),
        ended_on=profiles.parse_iso_date(_fuzzy_date(media.get("endDate"))),
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
            json_pointer=f"/{slug}",
        )
    await presentation.ensure_membership(session, entity_id=entity.entity_id, work_type="anime")
    return entity.entity_id


__all__ = [
    "MAPPER",
    "MAPPER_VERSION",
    "fact_candidates",
    "import_media",
    "name_entries",
]
