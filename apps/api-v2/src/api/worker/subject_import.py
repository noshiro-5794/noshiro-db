"""Atomic Bangumi work projection with reviewed aliases and explicit-ID reconciliation."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity import vndb
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.terms import preferred_terms
from api.worker import entities, facts, ingestion, metrics, presentation, profiles, records
from api.worker.subject_mapping import map_subject, work_facts

PROVIDER = "bangumi"
SUBJECT_NAMESPACE = "subject"
RESOURCE_TYPE = "subject"
MAPPER = "bangumi.subject"
MAPPER_VERSION = "bangumi-subject-v2"
SCHEMA_VERSION = "bangumi-api-v0"


async def normalize_subject(session: AsyncSession, mapped: dict[str, Any]) -> None:
    values = [mapped["platform"], *mapped["tags"], *(entry["key"] for entry in mapped["infobox"])]
    preferred = await preferred_terms(session, values)
    mapped["platform"] = preferred.get(mapped["platform"], mapped["platform"])[:256]
    tags = [preferred.get(tag, tag) for tag in mapped["tags"]]
    mapped["tags"] = [tag for tag in tags if tag]
    for entry in mapped["infobox"]:
        entry["key"] = preferred.get(entry["key"], entry["key"])
    mapped["infobox"] = [entry for entry in mapped["infobox"] if entry["key"] or entry["value"]]


def fact_pointer(slug: str, mapped: dict[str, Any], data: dict[str, Any]) -> str:
    if slug == "episode-count":
        return "/total_episodes" if mapped["total_episodes"] else "/eps"
    if slug == "series" and not isinstance(data.get("series"), bool):
        return ""
    return {
        "release-date": "/date",
        "platform": "/platform",
        "series": "/series",
        "volumes": "/volumes",
        "provider-infobox": "/infobox",
        "provider-tags": "/metatag" if data.get("meta_tags") is None else "/meta_tags",
    }[slug]


async def project_subject(
    session: AsyncSession,
    record_id: Any,
    data: dict[str, Any],
    *,
    mapper_version: str = MAPPER_VERSION,
) -> Any:
    mapped = map_subject(data)
    await normalize_subject(session, mapped)
    # Reviewed aliases can change while the source revision remains identical.
    observation_id = await ingestion.record_observation(
        session,
        provider_record_id=record_id,
        mapper=MAPPER,
        mapper_version=mapper_version,
        normalized_data={**data, "_projection_hash": ingestion.normalized_hash(mapped)},
        schema_name="index.work",
        schema_version="1",
    )
    entity = await entities.map_work(
        session,
        provider_record_id=record_id,
        mapped_data={"subject_type": mapped["subject_type"], "nsfw": mapped["nsfw"]},
    )
    await presentation.replace_names(
        session,
        entity_id=entity.entity_id,
        provider_record_id=record_id,
        observation_id=observation_id,
        original=mapped["title"],
        localized=mapped["title_cn"],
    )
    await presentation.upsert_description(
        session,
        entity_id=entity.entity_id,
        provider_record_id=record_id,
        observation_id=observation_id,
        text=mapped["description"],
    )
    await presentation.upsert_media(
        session,
        entity_id=entity.entity_id,
        provider_record_id=record_id,
        observation_id=observation_id,
        original=mapped["image_original"],
        thumbnail=mapped["image_thumbnail"],
    )
    if mapped["subject_type"] == "anime":
        await profiles.upsert_anime_profile(
            session,
            work_entity_id=entity.work_id,
            episode_count=mapped["total_episodes"] or mapped["eps"] or None,
            premiered_on=mapped["date"],
            replace_episode_count=True,
        )
    elif mapped["subject_type"] == "galgame":
        await fetch(
            session,
            """
            INSERT INTO galgame_profile
              (work_id, playtime_minutes, development_status, created_at, updated_at)
            VALUES (:work, NULL, '', now(), now()) ON CONFLICT DO NOTHING RETURNING work_id
            """,
            {"work": entity.work_id},
        )
    for slug, (value, value_type) in work_facts(mapped).items():
        await facts.record_fact(
            session,
            entity_id=entity.entity_id,
            observation_id=observation_id,
            slug=slug,
            name=slug.replace("-", " ").title(),
            value=value,
            value_type=value_type,
            json_pointer=fact_pointer(slug, mapped, data),
        )
    rating = data.get("rating")
    if isinstance(rating, dict):
        record = (
            await fetch(
                session, "SELECT last_seen_at FROM provider_record WHERE id=:id", {"id": record_id}
            )
        )[0]
        await metrics.record_metrics(
            session,
            entity_id=entity.entity_id,
            provider_record_id=record_id,
            observed_at=record.last_seen_at,
            values={
                "score": rating.get("score"),
                "rank": rating.get("rank"),
                "votes": rating.get("total"),
            },
        )
    await presentation.ensure_membership(
        session, entity_id=entity.entity_id, work_type=mapped["subject_type"]
    )
    return await vndb.observe_bangumi(session, entity.entity_id, observation_id, data)


async def import_subject(session: AsyncSession, data: dict[str, Any]) -> Any:
    """Persist a source payload and its complete work projection together."""
    async with session.begin_nested():
        written = await records.record_payload(
            session,
            provider_slug=PROVIDER,
            namespace_slug=SUBJECT_NAMESPACE,
            resource_type=RESOURCE_TYPE,
            external_id=str(data["id"]),
            payload=data,
            schema_version=SCHEMA_VERSION,
            canonical_url=f"https://bgm.tv/subject/{data['id']}",
        )
        return await project_subject(session, written.record_id, data)


async def provide_subject(session: AsyncSession, bangumi_id: str | int) -> Any:
    """Use an existing work identity or project a locally held embedded reference."""
    async with session.begin_nested():
        record_id = await records.ensure_record(
            session,
            provider_slug=PROVIDER,
            namespace_slug=SUBJECT_NAMESPACE,
            resource_type=RESOURCE_TYPE,
            external_id=str(bangumi_id),
            canonical_url=f"https://bgm.tv/subject/{bangumi_id}",
        )
        existing = await fetch(
            session,
            "SELECT r.entity_id FROM entity_representation r JOIN work w ON w.entity_id=r.entity_id"
            " WHERE r.provider_record_id=:record AND r.is_active"
            " ORDER BY r.created_at, r.id LIMIT 1",
            {"record": record_id},
        )
        if existing:
            from api.contexts.index.resolution import resolve

            return await resolve(session, existing[0].entity_id)
        rows = await fetch(
            session,
            "SELECT revision.payload FROM provider_record r JOIN provider_revision revision"
            " ON revision.id=r.latest_revision_id WHERE r.id=:record",
            {"record": record_id},
        )
        data = rows[0].payload if rows else {"embedded": True, "id": str(bangumi_id)}
        return await project_subject(
            session, record_id, data, mapper_version="bangumi-subject-placeholder-v2"
        )
