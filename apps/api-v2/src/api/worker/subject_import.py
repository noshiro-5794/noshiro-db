"""Import one Bangumi subject through the write primitives.

The order mirrors `project_work_from_record`: record the payload, record the observation it
produced, resolve the entity and its work row, then write what a visitor sees. Everything it
calls has already been exercised against the real schema on its own.

Not ported yet, and deliberately absent rather than silently skipped: the mapped *facts*
(a subject's infobox becomes entity facts) and the galgame profile row.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.worker import entities, ingestion, presentation, profiles, records
from api.worker.subject_mapping import map_subject

PROVIDER = "bangumi"
SUBJECT_NAMESPACE = "subject"
RESOURCE_TYPE = "subject"
MAPPER = "bangumi.subject"
MAPPER_VERSION = "bangumi-subject-v1"
SCHEMA_VERSION = "bangumi-api-v0"

ORIGINAL = "original"
TRANSLATED = "translated"


async def import_subject(session: AsyncSession, data: dict[str, Any]) -> Any:
    """Write one subject, returning the canonical entity id."""
    subject_id = str(data["id"])
    mapped = map_subject(data)
    written = await records.record_payload(
        session,
        provider_slug=PROVIDER,
        namespace_slug=SUBJECT_NAMESPACE,
        resource_type=RESOURCE_TYPE,
        external_id=subject_id,
        payload=data,
        schema_version=SCHEMA_VERSION,
        canonical_url=f"https://bgm.tv/subject/{subject_id}",
    )
    observation_id = await ingestion.record_observation(
        session,
        provider_record_id=written.record_id,
        mapper=MAPPER,
        mapper_version=MAPPER_VERSION,
        normalized_data=data,
        schema_name="index.work",
        schema_version="1",
    )
    entity = await entities.map_work(
        session,
        provider_record_id=written.record_id,
        mapped_data={"subject_type": mapped["subject_type"], "nsfw": mapped["nsfw"]},
    )

    names: list[tuple[str, str, str]] = []
    if mapped["title"]:
        names.append((mapped["title"], "", ORIGINAL))
    if mapped["title_cn"] and mapped["title_cn"] != mapped["title"]:
        names.append((mapped["title_cn"], "zh-Hans", TRANSLATED))
    if names:
        await presentation.add_names(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            entries=names,
        )
    if mapped["description"]:
        await presentation.upsert_description(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            text=mapped["description"],
        )
    if mapped["image_original"] or mapped["image_thumbnail"]:
        await presentation.upsert_media(
            session,
            entity_id=entity.entity_id,
            provider_record_id=written.record_id,
            observation_id=observation_id,
            original=mapped["image_original"],
            thumbnail=mapped["image_thumbnail"],
        )
    if mapped["subject_type"] == "anime":
        await profiles.upsert_anime_profile(
            session,
            work_entity_id=entity.work_id,
            media_format="",
            episode_count=mapped["total_episodes"] or mapped["eps"],
            premiered_on=mapped["date"],
        )
    await presentation.ensure_membership(
        session, entity_id=entity.entity_id, work_type=mapped["subject_type"]
    )
    return entity.entity_id


__all__ = [
    "MAPPER",
    "MAPPER_VERSION",
    "PROVIDER",
    "SCHEMA_VERSION",
    "SUBJECT_NAMESPACE",
    "import_subject",
]
