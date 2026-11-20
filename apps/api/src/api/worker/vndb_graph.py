"""VNDB embedded identities, contributor credits and evidence-backed relationships."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.names import SourceName
from api.contexts.ingestion import records
from api.contexts.ingestion.relations import credit, ensure_contributor, relation
from api.db import fetch
from api.worker import vndb_mapping as mapping
from api.worker.vndb_projection import (
    Projection,
    ensure_identity,
    record_source,
    write_description,
    write_links,
    write_names,
)


async def embedded_entity(
    session: AsyncSession,
    item: dict[str, Any],
    observation_id: Any,
    *,
    namespace: str,
    resource_type: str,
    kind: str,
) -> Projection | None:
    identifier = item.get("id")
    if not isinstance(identifier, str):
        return None
    record_id = await records.ensure_record(
        session,
        provider_slug="vndb",
        namespace_slug=namespace,
        resource_type=resource_type,
        external_id=identifier,
        canonical_url=f"https://vndb.org/{identifier}",
    )
    entity_id = await ensure_identity(session, record_id, kind=kind)
    projection = Projection(entity_id, record_id, observation_id)
    await write_names(session, projection, mapping.simple_names(item))
    return projection


async def producer(
    session: AsyncSession, item: dict[str, Any], observation_id: Any
) -> Projection | None:
    projection = await embedded_entity(
        session,
        item,
        observation_id,
        namespace="producer",
        resource_type="organization",
        kind="contributor",
    )
    if projection is not None:
        await ensure_contributor(session, projection.entity_id, "organization")
        await write_links(session, projection, item)
    return projection


async def staff(
    session: AsyncSession, item: dict[str, Any], observation_id: Any
) -> Projection | None:
    projection = await embedded_entity(
        session, item, observation_id, namespace="staff", resource_type="person", kind="contributor"
    )
    if projection is not None:
        await ensure_contributor(session, projection.entity_id, "person")
    return projection


async def bind_alias(
    session: AsyncSession,
    entity_id: Any,
    observation_id: Any,
    item: dict[str, Any],
    *,
    canonical_url: str = "",
) -> None:
    aid = item.get("aid")
    if not isinstance(aid, int) or isinstance(aid, bool):
        return
    record_id = await records.ensure_record(
        session,
        provider_slug="vndb",
        namespace_slug="staff-alias",
        resource_type="person",
        external_id=str(aid),
        canonical_url=canonical_url,
    )
    await fetch(
        session,
        """
        INSERT INTO entity_representation
          (id, provider_record_id, entity_id, mapping_kind, method, confidence,
           is_active, verified_at, created_at, updated_at)
        VALUES (gen_random_uuid(), :record, :entity, 'variant', 'provider', 1,
                true, NULL, now(), now())
        ON CONFLICT (provider_record_id, entity_id, mapping_kind) WHERE is_active
        DO UPDATE SET method=EXCLUDED.method, confidence=1, updated_at=now()
        RETURNING id
        """,
        {"record": record_id, "entity": entity_id},
    )
    names = []
    for field, kind in (("name", "alias"), ("latin", "romanized")):
        value = item.get(field)
        if isinstance(value, str) and value:
            names.append(SourceName(value, "", kind))
    await write_names(session, Projection(entity_id, record_id, observation_id), names)


async def import_staff(session: AsyncSession, items: tuple[dict[str, Any], ...]) -> None:
    for item in items:
        if not isinstance(item.get("id"), str):
            continue
        record_id, observation_id = await record_source(
            session,
            item,
            namespace="staff",
            resource_type="person",
            mapper="vndb.staff",
            mapper_version="vndb-staff-v1",
            schema_name="index.contributor",
        )
        entity_id = await ensure_identity(session, record_id, kind="contributor", exact_only=False)
        await ensure_contributor(session, entity_id, "person")
        projection = Projection(entity_id, record_id, observation_id)
        await write_names(session, projection, mapping.simple_names(item))
        for alias in item.get("aliases") or []:
            await bind_alias(
                session,
                entity_id,
                observation_id,
                alias,
                canonical_url=f"https://vndb.org/{item['id']}",
            )
        await write_description(session, projection, item)
        await write_links(session, projection, item)


async def import_credits(session: AsyncSession, work: Projection, data: dict[str, Any]) -> None:
    for item in data.get("developers") or []:
        contributor = await producer(session, item, work.observation_id)
        if contributor is not None:
            await credit(
                session,
                work.entity_id,
                contributor.entity_id,
                work.observation_id,
                role="developer",
                credited_as=mapping.credited_name(item),
            )
    for item in data.get("staff") or []:
        contributor = await staff(session, item, work.observation_id)
        role = item.get("role")
        if contributor is None or not isinstance(role, str) or not role:
            continue
        await bind_alias(session, contributor.entity_id, work.observation_id, item)
        await credit(
            session,
            work.entity_id,
            contributor.entity_id,
            work.observation_id,
            role=role,
            credited_as=mapping.credited_name(item),
        )


async def import_relations(session: AsyncSession, work: Projection, data: dict[str, Any]) -> None:
    for index, item in enumerate(data.get("relations") or []):
        target = await embedded_entity(
            session, item, work.observation_id, namespace="vn", resource_type="subject", kind="work"
        )
        if target is None or target.entity_id == work.entity_id:
            continue
        await fetch(
            session,
            """
            INSERT INTO work (entity_id, work_type, popularity, popularity_refreshed_at,
                              created_at, updated_at)
            VALUES (:id, 'galgame', 0, NULL, now(), now()) ON CONFLICT DO NOTHING
            RETURNING entity_id
            """,
            {"id": target.entity_id},
        )
        await relation(
            session,
            work.entity_id,
            target.entity_id,
            work.observation_id,
            relation_type=mapping.relation_type(item.get("relation")),
            json_pointer=f"/relations/{index}",
            raw_relation=str(item.get("relation") or ""),
            qualifiers={"official": bool(item.get("relation_official"))},
        )


async def import_voices(session: AsyncSession, work: Projection, data: dict[str, Any]) -> None:
    for item in data.get("va") or []:
        staff_data, character_data = item.get("staff"), item.get("character")
        if not isinstance(staff_data, dict) or not isinstance(character_data, dict):
            continue
        contributor = await staff(session, staff_data, work.observation_id)
        character = await embedded_entity(
            session,
            character_data,
            work.observation_id,
            namespace="character",
            resource_type="character",
            kind="character",
        )
        if contributor is None or character is None:
            continue
        await bind_alias(session, contributor.entity_id, work.observation_id, staff_data)
        appearances = await fetch(
            session,
            """
            SELECT a.id FROM appearance AS a
            WHERE a.work_id=:work AND a.character_entity_id=:character
              AND (a.observation_id IS NULL OR EXISTS (
                SELECT 1 FROM provider_observation AS o
                JOIN provider_record AS r ON r.id=o.provider_record_id
                JOIN provider_namespace AS ns ON ns.id=r.namespace_id
                JOIN provider AS p ON p.id=ns.provider_id
                JOIN provider_current_observation AS c
                  ON c.observation_id=o.id AND c.provider_record_id=r.id
                WHERE o.id=a.observation_id AND r.status='active'
                  AND p.redistribution_policy<>'forbidden'
              )) ORDER BY a.id LIMIT 1
            """,
            {"work": work.entity_id, "character": character.entity_id},
        )
        if not appearances:
            appearances = await fetch(
                session,
                """
                INSERT INTO appearance
                  (work_id, character_entity_id, role, observation_id, spoiler_level,
                   created_at, updated_at)
                VALUES (:work, :character, '', :observation, 0, now(), now())
                ON CONFLICT (work_id, character_entity_id, role, observation_id)
                DO UPDATE SET role=EXCLUDED.role RETURNING id
                """,
                {
                    "work": work.entity_id,
                    "character": character.entity_id,
                    "observation": work.observation_id,
                },
            )
        await fetch(
            session,
            """
            INSERT INTO voice_performance
              (appearance_id, contributor_id, language, observation_id, credited_as,
               created_at, updated_at)
            VALUES (:appearance, :contributor, :language, :observation, :name, now(), now())
            ON CONFLICT DO NOTHING RETURNING id
            """,
            {
                "appearance": appearances[0].id,
                "contributor": contributor.entity_id,
                "language": staff_data.get("lang") or "",
                "observation": work.observation_id,
                "name": mapping.credited_name(staff_data),
            },
        )
