"""Bangumi relationship collections and their observation-scoped graph edges."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.relations import canonical_relation_type
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.terms import preferred_terms
from api.worker import graph, ingestion, records
from api.worker.bangumi_entities import provide_entity
from api.worker.subject_import import provide_subject


@dataclass(frozen=True, slots=True)
class RelatedIds:
    subjects: set[str]
    staff: set[str]
    characters: set[str]


def source_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    identifier = item.get("id")
    return (
        str(identifier)
        if isinstance(identifier, int) and not isinstance(identifier, bool)
        else None
    )


def collect_ids(items: list[Any]) -> set[str]:
    result = set()
    for item in items:
        identifier = source_id(item)
        if identifier is not None:
            result.add(identifier)
    return result


def related_ids(subjects: list[Any], staff: list[Any], characters: list[Any]) -> RelatedIds:
    people = collect_ids(staff)
    for item in characters:
        if isinstance(item, dict) and isinstance(item.get("actors"), list):
            people.update(collect_ids(item["actors"]))
    return RelatedIds(collect_ids(subjects), people, collect_ids(characters))


def role_for(item: dict[str, Any], preferred: dict[str, str]) -> str:
    raw = str(item.get("relation") or "").strip()
    return preferred.get(raw, raw)


async def collection(
    session: AsyncSession,
    subject_id: str,
    namespace: str,
    schema: str,
    path: str,
    items: list[Any],
    preferred: dict[str, str],
) -> Any:
    payload = {"items": items}
    recorded = await records.record_payload(
        session,
        provider_slug="bangumi",
        namespace_slug=namespace,
        resource_type="collection",
        external_id=subject_id,
        payload=payload,
        canonical_url=f"https://bgm.tv/subject/{subject_id}/{path}",
        schema_version="bangumi-api-v0",
    )
    return await ingestion.record_observation(
        session,
        provider_record_id=recorded.record_id,
        mapper=f"bangumi.{namespace}",
        mapper_version=f"bangumi-{namespace}-v2",
        normalized_data={
            **payload,
            "_projection_hash": ingestion.normalized_hash(
                [role_for(item, preferred) for item in items if isinstance(item, dict)]
            ),
        },
        schema_name=schema,
        schema_version="1",
    )


async def import_relations(
    session: AsyncSession,
    work_id: Any,
    subject_id: str,
    *,
    subjects: list[Any] | None,
    staff: list[Any] | None,
    characters: list[Any] | None,
) -> RelatedIds:
    async with session.begin_nested():
        identifiers = related_ids(subjects or [], staff or [], characters or [])
        works = {
            identifier: await provide_subject(session, identifier)
            for identifier in sorted(identifiers.subjects, key=int)
        }
        people = {
            identifier: await provide_entity(session, identifier, "person")
            for identifier in sorted(identifiers.staff, key=int)
        }
        character_map = {
            identifier: await provide_entity(session, identifier, "character")
            for identifier in sorted(identifiers.characters, key=int)
        }
        values = [
            str(item.get("relation") or "")
            for item in [*(subjects or []), *(staff or []), *(characters or [])]
            if isinstance(item, dict)
        ]
        preferred = await preferred_terms(session, values)
        if subjects is not None:
            observation = await collection(
                session,
                subject_id,
                "subject-relations",
                "index.work.relations",
                "relations",
                subjects,
                preferred,
            )
            for index, item in enumerate(subjects):
                identifier = source_id(item)
                if identifier is None:
                    continue
                target = works.get(identifier)
                if target is None or target == work_id:
                    continue
                raw = str(item.get("relation") or "")
                await graph.relation(
                    session,
                    work_id,
                    target,
                    observation,
                    relation_type=canonical_relation_type(role_for(item, preferred)),
                    json_pointer=f"/items/{index}",
                    raw_relation=raw,
                )
        if staff is not None:
            observation = await collection(
                session,
                subject_id,
                "subject-staff",
                "index.work.credits",
                "staff",
                staff,
                preferred,
            )
            for item in staff:
                identifier = source_id(item)
                if identifier is None:
                    continue
                person = people.get(identifier)
                if person is None:
                    continue
                await graph.credit(
                    session,
                    work_id,
                    person,
                    observation,
                    role=role_for(item, preferred) or "staff",
                    credited_as=str(item.get("name") or "")[:512],
                )
        if characters is not None:
            observation = await collection(
                session,
                subject_id,
                "subject-characters",
                "index.work.characters",
                "characters",
                characters,
                preferred,
            )
            for item in characters:
                identifier = source_id(item)
                if identifier is None:
                    continue
                character = character_map.get(identifier)
                if character is None:
                    continue
                appearance = (
                    await fetch(
                        session,
                        """
                    INSERT INTO appearance
                      (work_id, character_entity_id, role, observation_id, spoiler_level,
                       created_at, updated_at)
                    VALUES (:work, :character, :role, :observation, 0, now(), now())
                    ON CONFLICT (work_id, character_entity_id, role, observation_id)
                    DO UPDATE SET role=EXCLUDED.role RETURNING id
                """,
                        {
                            "work": work_id,
                            "character": character,
                            "role": role_for(item, preferred),
                            "observation": observation,
                        },
                    )
                )[0]
                for actor in item.get("actors") or []:
                    actor_id = source_id(actor)
                    if actor_id is None:
                        continue
                    contributor = people.get(actor_id)
                    if contributor is None:
                        continue
                    await fetch(
                        session,
                        """
                        INSERT INTO voice_performance
                          (appearance_id, contributor_id, language, observation_id, credited_as,
                           created_at, updated_at)
                        VALUES (:appearance, :contributor, '', :observation, :name, now(), now())
                        ON CONFLICT DO NOTHING RETURNING id
                    """,
                        {
                            "appearance": appearance.id,
                            "contributor": contributor,
                            "observation": observation,
                            "name": str(actor.get("name") or "")[:512],
                        },
                    )
        return identifiers
