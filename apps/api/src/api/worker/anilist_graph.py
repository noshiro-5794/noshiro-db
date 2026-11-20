"""AniList genres, tags, related works, characters, staff, studios and voices."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.relations import canonical_relation_type
from api.contexts.ingestion import entities, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import relations as graph
from api.db import fetch
from api.shared.text import slugify


async def embedded_entity(
    session: AsyncSession,
    node: dict[str, Any],
    observation_id: Any,
    *,
    namespace: str,
    resource_type: str,
    kind: str,
    path: str,
    name: Any,
) -> Any:
    identifier = node.get("id")
    if not isinstance(identifier, int) or isinstance(identifier, bool):
        return None
    record_id = await records.ensure_record(
        session,
        provider_slug="anilist",
        namespace_slug=namespace,
        resource_type=resource_type,
        external_id=str(identifier),
        canonical_url=f"https://anilist.co/{path}/{identifier}",
    )
    entity_id, _ = await entities.ensure_entity(
        session,
        provider_record_id=record_id,
        kind=kind,
        audience="unknown",
        preserve_existing=True,
    )
    await entities.upsert_representation(session, provider_record_id=record_id, entity_id=entity_id)
    if isinstance(name, str) and name:
        await presentation.add_names(
            session,
            entity_id=entity_id,
            provider_record_id=record_id,
            observation_id=observation_id,
            entries=[(name, "", "official")],
        )
    return entity_id


def full_name(node: dict[str, Any]) -> Any:
    name = node.get("name") or {}
    return name.get("full") or name.get("native")


def edges(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("edges")
    return [item for item in value or [] if isinstance(item, dict)]


async def person(session: AsyncSession, node: dict[str, Any], observation_id: Any) -> Any:
    entity_id = await embedded_entity(
        session,
        node,
        observation_id,
        namespace="staff",
        resource_type="person",
        kind="contributor",
        path="staff",
        name=full_name(node),
    )
    if entity_id is not None:
        await graph.ensure_contributor(session, entity_id, "person")
    return entity_id


async def import_graph(
    session: AsyncSession, work_id: Any, observation_id: Any, media: dict[str, Any]
) -> None:
    await import_terms(session, work_id, observation_id, media)
    for index, edge in enumerate(edges(media.get("relations"))):
        node, raw = edge.get("node") or {}, edge.get("relationType")
        if not isinstance(raw, str) or not isinstance(node, dict):
            continue
        title = node.get("title") or {}
        target = await embedded_entity(
            session,
            node,
            observation_id,
            namespace="anime",
            resource_type="subject",
            kind="work",
            path="anime",
            name=title.get("romaji") or title.get("english") or title.get("native"),
        )
        if target is None or target == work_id:
            continue
        await fetch(
            session,
            """
            INSERT INTO work
              (entity_id, work_type, popularity, popularity_refreshed_at, created_at, updated_at)
            VALUES (:entity, :type, 0, NULL, now(), now())
            ON CONFLICT DO NOTHING RETURNING entity_id
            """,
            {
                "entity": target,
                "type": "anime"
                if node.get("format")
                in {
                    "TV",
                    "TV_SHORT",
                    "MOVIE",
                    "OVA",
                    "ONA",
                    "SPECIAL",
                    "MUSIC",
                }
                else "other",
            },
        )
        await graph.relation(
            session,
            work_id,
            target,
            observation_id,
            relation_type=canonical_relation_type(raw),
            json_pointer=f"/relations/edges/{index}",
            raw_relation=raw,
        )
    for edge in edges(media.get("characters")):
        node = edge.get("node") or {}
        character = await embedded_entity(
            session,
            node,
            observation_id,
            namespace="character",
            resource_type="character",
            kind="character",
            path="character",
            name=full_name(node),
        )
        if character is None:
            continue
        appearance = await fetch(
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
                "role": edge.get("role") or "",
                "observation": observation_id,
            },
        )
        for actor in edge.get("voiceActors") or []:
            if not isinstance(actor, dict):
                continue
            contributor = await person(session, actor, observation_id)
            if contributor is None:
                continue
            await fetch(
                session,
                """
                INSERT INTO voice_performance
                  (appearance_id, contributor_id, observation_id, language, credited_as,
                   created_at, updated_at)
                VALUES (:appearance, :contributor, :observation, '', '', now(), now())
                ON CONFLICT DO NOTHING RETURNING id
                """,
                {
                    "appearance": appearance[0].id,
                    "contributor": contributor,
                    "observation": observation_id,
                },
            )
    for edge in edges(media.get("staff")):
        contributor = await person(session, edge.get("node") or {}, observation_id)
        if contributor is not None:
            await graph.credit(
                session,
                work_id,
                contributor,
                observation_id,
                role=edge.get("role") or "",
                credited_as="",
            )
    for edge in edges(media.get("studios")):
        node = edge.get("node") or {}
        contributor = await embedded_entity(
            session,
            node,
            observation_id,
            namespace="studio",
            resource_type="organization",
            kind="contributor",
            path="studio",
            name=node.get("name"),
        )
        if contributor is not None:
            await graph.ensure_contributor(session, contributor, "organization")
            await graph.credit(
                session, work_id, contributor, observation_id, role="Studio", credited_as=""
            )


async def import_terms(
    session: AsyncSession, work_id: Any, observation_id: Any, media: dict[str, Any]
) -> None:
    for namespace, name, values in (
        ("genre", "AniList Genres", media.get("genres") or []),
        (
            "tag",
            "AniList Tags",
            [item.get("name") for item in media.get("tags") or [] if isinstance(item, dict)],
        ),
    ):
        taxonomy = await fetch(
            session,
            """
            INSERT INTO taxonomy (slug, name, description) VALUES (:slug, :name, '')
            ON CONFLICT (slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
            """,
            {"slug": f"anilist-{namespace}s", "name": name},
        )
        for value in values:
            if not isinstance(value, str) or not value:
                continue
            slug = slugify(value)
            record_id = await records.ensure_record(
                session,
                provider_slug="anilist",
                namespace_slug=namespace,
                resource_type="taxonomy",
                external_id=slug,
                canonical_url=f"https://anilist.co/search/anime?{slug}",
            )
            term = await fetch(
                session,
                """
                INSERT INTO taxonomy_term (taxonomy_id, slug, parent_id)
                VALUES (:taxonomy, :slug, NULL)
                ON CONFLICT (taxonomy_id, slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
                """,
                {"taxonomy": taxonomy[0].id, "slug": slug},
            )
            await fetch(
                session,
                """
                INSERT INTO taxonomy_term_label (term_id, language, script, text, is_preferred)
                VALUES (:term, 'en', 'Latn', :name, true) ON CONFLICT DO NOTHING RETURNING id
                """,
                {"term": term[0].id, "name": value},
            )
            await fetch(
                session,
                """
                INSERT INTO taxonomy_term_mapping (term_id, provider_record_id, confidence)
                VALUES (:term, :record, 1) ON CONFLICT DO NOTHING RETURNING id
                """,
                {"term": term[0].id, "record": record_id},
            )
            await fetch(
                session,
                """
                INSERT INTO entity_term
                  (entity_id, term_id, observation_id, relevance, spoiler_level)
                VALUES (:entity, :term, :observation, 1, 0) ON CONFLICT DO NOTHING RETURNING id
                """,
                {"entity": work_id, "term": term[0].id, "observation": observation_id},
            )
