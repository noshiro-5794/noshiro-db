"""Bangumi episode collections with deterministic identities and retained evidence."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.ingestion import entities, facts, metrics, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import observations as ingestion
from api.contexts.ingestion import relations as graph
from api.db import fetch
from api.worker.subject_mapping import clean_string

EPISODE_NAMESPACE = UUID("1e6aface-b51d-4cf9-b37a-7dd12beb2e2e")


def decimal_value(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def episode_facts(data: dict[str, Any]) -> list[tuple[str, Any, str]]:
    duration = data.get("duration_seconds")
    raw_date = clean_string(data.get("airdate"))
    try:
        air_date = date.fromisoformat(raw_date).isoformat()
    except ValueError:
        air_date = None
    source_type = data.get("type")
    episode_type = None
    if isinstance(source_type, int):
        episode_type = {0: "EP", 1: "SP", 2: "OP", 3: "ED", 4: "PV/CM", 5: "MAD", 6: "ETC"}.get(
            source_type
        )
    values = [
        ("episode-type", episode_type, "/type"),
        ("episode-number", decimal_value(data.get("ep")), "/ep"),
        ("sort", decimal_value(data.get("sort")), "/sort"),
        (
            "duration-seconds",
            float(duration) if isinstance(duration, int) and duration > 0 else None,
            "/duration_seconds",
        ),
        ("air-date", air_date, "/airdate"),
        ("disc", data.get("disc"), "/disc"),
        ("raw-duration", clean_string(data.get("duration"), max_length=64) or None, "/duration"),
    ]
    result = []
    for slug, value, pointer in values:
        if slug == "disc" and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            continue
        if value is None:
            continue
        result.append((slug, str(value) if isinstance(value, Decimal) else value, pointer))
    return result


async def episode_identity(
    session: AsyncSession, record_id: Any, external_id: str, audience: str
) -> Any:
    existing = await fetch(
        session,
        "SELECT entity_id FROM entity_representation WHERE provider_record_id=:record"
        " AND is_active ORDER BY created_at, id LIMIT 1",
        {"record": record_id},
    )
    identifier = (
        existing[0].entity_id if existing else uuid5(EPISODE_NAMESPACE, f"episode:{external_id}")
    )
    row = (
        await fetch(
            session,
            """
        INSERT INTO entity
          (id, kind, lifecycle, visibility, audience, spoiler_level, created_at, updated_at)
        VALUES (:id, 'episode', 'active', 'public', :audience, 0, now(), now())
        ON CONFLICT (id) DO UPDATE SET id=EXCLUDED.id RETURNING id, kind, audience
    """,
            {"id": identifier, "audience": audience},
        )
    )[0]
    if row.kind != "episode":
        raise ValueError(f"Episode {external_id} entity UUID collides with {row.kind}.")
    if audience == "adult" and row.audience != "adult":
        await fetch(
            session,
            "UPDATE entity SET audience='adult', updated_at=now() WHERE id=:id RETURNING id",
            {"id": identifier},
        )
    await entities.upsert_representation(
        session, provider_record_id=record_id, entity_id=identifier
    )
    return identifier


async def import_episodes(
    session: AsyncSession, work_id: Any, subject_id: str, items: list[Any]
) -> None:
    async with session.begin_nested():
        payload = {"items": items}
        collection = await records.record_payload(
            session,
            provider_slug="bangumi",
            namespace_slug="subject-episodes",
            resource_type="collection",
            external_id=subject_id,
            payload=payload,
            canonical_url=f"https://bgm.tv/subject/{subject_id}/ep",
            schema_version="bangumi-api-v0",
        )
        relationship = await ingestion.record_observation(
            session,
            provider_record_id=collection.record_id,
            mapper="bangumi.subject-episodes",
            mapper_version="bangumi-subject-episodes-v1",
            normalized_data=payload,
            schema_name="index.work.episodes",
            schema_version="1",
        )
        unique = {
            str(item["id"]): (index, item)
            for index, item in enumerate(items)
            if isinstance(item, dict) and item.get("id")
        }
        audience = (
            await fetch(session, "SELECT audience FROM entity WHERE id=:id", {"id": work_id})
        )[0].audience
        for external_id, (index, item) in unique.items():
            recorded = await records.record_payload(
                session,
                provider_slug="bangumi",
                namespace_slug="episode",
                resource_type="episode",
                external_id=external_id,
                payload=item,
                canonical_url=f"https://bgm.tv/ep/{external_id}",
                schema_version="bangumi-api-v0",
            )
            observation = await ingestion.record_observation(
                session,
                provider_record_id=recorded.record_id,
                mapper="bangumi.episode",
                mapper_version="bangumi-episode-v2",
                normalized_data=item,
                schema_name="index.episode",
                schema_version="1",
            )
            entity_id = await episode_identity(session, recorded.record_id, external_id, audience)
            await presentation.replace_names(
                session,
                entity_id=entity_id,
                provider_record_id=recorded.record_id,
                observation_id=observation,
                original=clean_string(item.get("name"), max_length=256),
                localized=clean_string(item.get("name_cn"), max_length=256),
            )
            await presentation.upsert_description(
                session,
                entity_id=entity_id,
                provider_record_id=recorded.record_id,
                observation_id=observation,
                text=clean_string(item.get("desc")),
            )
            for slug, value, pointer in episode_facts(item):
                if isinstance(value, bool):
                    value_type = "boolean"
                elif isinstance(value, int | float):
                    value_type = "number"
                else:
                    value_type = "string"
                await facts.record_fact(
                    session,
                    entity_id=entity_id,
                    observation_id=observation,
                    slug=slug,
                    name=slug.replace("-", " ").title(),
                    value=value,
                    value_type=value_type,
                    json_pointer=pointer,
                )
            await metrics.record_metrics(
                session,
                entity_id=entity_id,
                provider_record_id=recorded.record_id,
                observed_at=await ingestion.observed_at(session, observation),
                values={"comment-count": item.get("comment")},
            )
            await graph.relation(
                session,
                work_id,
                entity_id,
                relationship,
                relation_type="has-episode",
                json_pointer=f"/items/{index}",
                raw_relation="has-episode",
            )
