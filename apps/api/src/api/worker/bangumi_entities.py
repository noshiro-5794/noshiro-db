"""Bangumi character/person projections and cached relationship identities."""

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index.resolution import resolve
from api.contexts.ingestion import entities, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import observations as ingestion
from api.contexts.ingestion import relations as graph
from api.db import fetch
from api.worker.subject_mapping import clean_string, image_urls

Namespace = Literal["character", "person"]


async def project_entity(
    session: AsyncSession,
    record_id: Any,
    data: dict[str, Any],
    namespace: Namespace,
    *,
    placeholder: bool = False,
) -> Any:
    character = namespace == "character"
    observation = await ingestion.record_observation(
        session,
        provider_record_id=record_id,
        mapper=f"bangumi.{namespace}",
        mapper_version=f"bangumi-{namespace}-{'placeholder-' if placeholder else ''}v2",
        normalized_data=data,
        schema_name="index.character" if character else "index.contributor",
        schema_version="1",
    )
    entity_id, _ = await entities.ensure_entity(
        session,
        provider_record_id=record_id,
        kind="character" if character else "contributor",
        audience="unknown",
        preserve_existing=True,
    )
    await entities.upsert_representation(session, provider_record_id=record_id, entity_id=entity_id)
    if not character:
        source_type = data.get("type")
        kind = "unknown"
        if isinstance(source_type, int):
            kind = {1: "person", 2: "organization", 3: "organization"}.get(source_type, "unknown")
        await graph.ensure_contributor(session, entity_id, kind)
    await presentation.replace_names(
        session,
        entity_id=entity_id,
        provider_record_id=record_id,
        observation_id=observation,
        original=clean_string(data.get("name"), max_length=256),
    )
    await presentation.upsert_description(
        session,
        entity_id=entity_id,
        provider_record_id=record_id,
        observation_id=observation,
        text=clean_string(data.get("summary")),
    )
    if character:
        original, thumbnail = image_urls(data)
        await presentation.upsert_media(
            session,
            entity_id=entity_id,
            provider_record_id=record_id,
            observation_id=observation,
            original=original,
            thumbnail=thumbnail,
        )
    return await resolve(session, entity_id)


async def import_entity(session: AsyncSession, data: dict[str, Any], namespace: Namespace) -> Any:
    async with session.begin_nested():
        written = await records.record_payload(
            session,
            provider_slug="bangumi",
            namespace_slug=namespace,
            resource_type=namespace,
            external_id=str(data["id"]),
            payload=data,
            schema_version="bangumi-api-v0",
            canonical_url=f"https://bgm.tv/{namespace}/{data['id']}",
        )
        return await project_entity(session, written.record_id, data, namespace)


async def provide_entity(session: AsyncSession, external_id: str, namespace: Namespace) -> Any:
    async with session.begin_nested():
        record_id = await records.ensure_record(
            session,
            provider_slug="bangumi",
            namespace_slug=namespace,
            resource_type=namespace,
            external_id=external_id,
            canonical_url=f"https://bgm.tv/{namespace}/{external_id}",
        )
        rows = await fetch(
            session,
            "SELECT entity_id FROM entity_representation WHERE provider_record_id=:record"
            " AND is_active ORDER BY created_at, id LIMIT 1",
            {"record": record_id},
        )
        if rows:
            entity_id = rows[0].entity_id
            if namespace == "character":
                return await resolve(session, entity_id)
            contributor = await fetch(
                session, "SELECT entity_id FROM contributor WHERE entity_id=:id", {"id": entity_id}
            )
            if contributor:
                return await resolve(session, entity_id)
        saved = await fetch(
            session,
            "SELECT revision.payload FROM provider_record r JOIN provider_revision revision"
            " ON revision.id=r.latest_revision_id WHERE r.id=:record",
            {"record": record_id},
        )
        payload = saved[0].payload if saved else {"embedded": True, "id": external_id}
        return await project_entity(session, record_id, payload, namespace, placeholder=True)
