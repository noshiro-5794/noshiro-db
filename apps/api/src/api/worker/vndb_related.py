"""VNDB release and character projections backed by a related-batch observation."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.names import SourceName
from api.contexts.ingestion import records
from api.contexts.ingestion.relations import relation
from api.db import fetch
from api.worker import vndb_mapping as mapping
from api.worker.vndb_graph import producer
from api.worker.vndb_projection import (
    Projection,
    ensure_identity,
    record_source,
    write_description,
    write_facts,
    write_links,
    write_media,
    write_names,
)


async def import_releases(
    session: AsyncSession,
    work_id: Any,
    vndb_id: str,
    observation_id: Any,
    items: tuple[dict[str, Any], ...],
) -> None:
    for index, item in enumerate(items):
        if not isinstance(item.get("id"), str):
            continue
        record_id, source_observation = await record_source(
            session,
            item,
            namespace="release",
            resource_type="release",
            mapper="vndb.release",
            mapper_version="vndb-release-v1",
            schema_name="index.release",
        )
        min_age = mapping.positive_int(item.get("minage"))
        entity_id = await ensure_identity(
            session,
            record_id,
            kind="release",
            audience="adult" if (min_age or 0) >= 18 else "general",
            exact_only=False,
        )
        projection = Projection(entity_id, record_id, source_observation)
        start, end, precision = mapping.partial_date(item.get("released"))
        await fetch(
            session,
            """
            INSERT INTO release
              (entity_id, release_type, date_start, date_end, date_precision, date_raw,
               platform, region, is_official, is_patch, created_at, updated_at)
            VALUES (:id, :type, :start, :end, :precision, :raw, :platform, '',
                    :official, :patch, now(), now())
            ON CONFLICT (entity_id) DO UPDATE
              SET release_type=EXCLUDED.release_type, date_start=EXCLUDED.date_start,
                  date_end=EXCLUDED.date_end, date_precision=EXCLUDED.date_precision,
                  date_raw=EXCLUDED.date_raw, platform=EXCLUDED.platform,
                  is_official=EXCLUDED.is_official, is_patch=EXCLUDED.is_patch, updated_at=now()
            RETURNING entity_id
            """,
            {
                "id": entity_id,
                "type": "patch" if item.get("patch") else "edition",
                "start": start,
                "end": end,
                "precision": precision,
                "raw": item.get("released") or "",
                "platform": ",".join(item.get("platforms") or [])[:64],
                "official": item.get("official"),
                "patch": bool(item.get("patch")),
            },
        )
        for vn_index, vn in enumerate(item.get("vns") or []):
            if vn.get("id") != vndb_id:
                continue
            raw_role = vn.get("rtype") or "complete"
            link = await fetch(
                session,
                """
                INSERT INTO release_work (release_id, work_id, role)
                VALUES (:release, :work, :role)
                ON CONFLICT (release_id, work_id, role)
                DO UPDATE SET role=EXCLUDED.role RETURNING id
                """,
                {
                    "release": entity_id,
                    "work": work_id,
                    "role": mapping.release_work_role(raw_role),
                },
            )
            await fetch(
                session,
                """
                INSERT INTO release_work_evidence
                  (release_work_id, observation_id, json_pointer, raw_role, created_at, updated_at)
                VALUES (:link, :observation, :pointer, :raw, now(), now())
                ON CONFLICT DO NOTHING RETURNING id
                """,
                {
                    "link": link[0].id,
                    "observation": observation_id,
                    "pointer": f"/releases/{index}/vns/{vn_index}",
                    "raw": str(raw_role)[:64],
                },
            )
        title = item.get("title") or item.get("alttitle")
        if isinstance(title, str) and title:
            await write_names(
                session, projection, [SourceName(title, "", "official", is_official=True)]
            )
        if min_age is not None:
            await fetch(
                session,
                """
                INSERT INTO content_rating
                  (entity_id, system, value, region, provider_record_id, observation_id,
                   minimum_age, created_at, updated_at)
                VALUES (:entity, 'vndb-minage', :value, '', :record, :observation,
                        :age, now(), now())
                ON CONFLICT DO NOTHING RETURNING id
                """,
                {
                    "entity": entity_id,
                    "value": str(min_age),
                    "record": record_id,
                    "observation": source_observation,
                    "age": min_age,
                },
            )
        await write_links(session, projection, item)
        await write_facts(session, projection, mapping.release_facts(item))
        for producer_index, producer_data in enumerate(item.get("producers") or []):
            contributor = await producer(session, producer_data, source_observation)
            if contributor is None:
                continue
            roles = []
            if producer_data.get("developer"):
                roles.append("release-developer")
            if producer_data.get("publisher"):
                roles.append("release-publisher")
            for role in roles:
                await relation(
                    session,
                    entity_id,
                    contributor.entity_id,
                    source_observation,
                    relation_type=role,
                    json_pointer=f"/producers/{producer_index}",
                    raw_relation=role,
                )


async def import_characters(
    session: AsyncSession,
    work_id: Any,
    vndb_id: str,
    observation_id: Any,
    items: tuple[dict[str, Any], ...],
) -> None:
    for item in items:
        if not isinstance(item.get("id"), str):
            continue
        record_id, source_observation = await record_source(
            session,
            item,
            namespace="character",
            resource_type="character",
            mapper="vndb.character",
            mapper_version="vndb-character-v1",
            schema_name="index.character",
        )
        entity_id = await ensure_identity(session, record_id, kind="character", exact_only=False)
        projection = Projection(entity_id, record_id, source_observation)
        await write_names(session, projection, mapping.simple_names(item))
        await write_description(session, projection, item)
        await write_media(session, projection, item.get("image") or {}, purpose="poster")
        appearances = [row for row in item.get("vns") or [] if row.get("id") == vndb_id]
        if appearances:
            await fetch(
                session,
                """
                INSERT INTO appearance
                  (work_id, character_entity_id, role, observation_id, spoiler_level,
                   created_at, updated_at)
                VALUES (:work, :character, :role, :observation, :spoiler, now(), now())
                ON CONFLICT DO NOTHING RETURNING id
                """,
                {
                    "work": work_id,
                    "character": entity_id,
                    "role": appearances[0].get("role") or "",
                    "observation": observation_id,
                    "spoiler": max(
                        mapping.spoiler_level(row.get("spoiler")) for row in appearances
                    ),
                },
            )
        await write_traits(session, projection, item.get("traits") or [])
        await write_facts(session, projection, mapping.character_facts(item))


async def term_label(session: AsyncSession, term_id: Any, name: str) -> None:
    await fetch(
        session,
        """
        INSERT INTO taxonomy_term_label (term_id, language, script, text, is_preferred)
        VALUES (:term, 'en', 'Latn', :name, true) ON CONFLICT DO NOTHING RETURNING id
        """,
        {"term": term_id, "name": name},
    )


async def write_traits(
    session: AsyncSession, projection: Projection, items: list[dict[str, Any]]
) -> None:
    taxonomy = await fetch(
        session,
        """
        INSERT INTO taxonomy (slug, name, description)
        VALUES ('vndb-traits', 'VNDB Character Traits', '')
        ON CONFLICT (slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
        """,
        {},
    )
    for index, item in enumerate(items):
        identifier, name = item.get("id"), item.get("name")
        if not isinstance(identifier, str) or not isinstance(name, str):
            continue
        record_id = await records.ensure_record(
            session,
            provider_slug="vndb",
            namespace_slug="trait",
            resource_type="taxonomy",
            external_id=identifier,
            canonical_url=f"https://vndb.org/{identifier}",
        )
        parent_id = None
        group_id = item.get("group_id")
        if isinstance(group_id, str) and group_id:
            parent = await fetch(
                session,
                """
                INSERT INTO taxonomy_term (taxonomy_id, slug, parent_id)
                VALUES (:taxonomy, :slug, NULL)
                ON CONFLICT (taxonomy_id, slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
                """,
                {"taxonomy": taxonomy[0].id, "slug": f"group-{group_id}"},
            )
            parent_id = parent[0].id
            group_name = item.get("group_name")
            if isinstance(group_name, str) and group_name:
                await term_label(session, parent_id, group_name)
        term = await fetch(
            session,
            """
            INSERT INTO taxonomy_term (taxonomy_id, slug, parent_id)
            VALUES (:taxonomy, :slug, :parent)
            ON CONFLICT (taxonomy_id, slug) DO UPDATE SET parent_id=EXCLUDED.parent_id RETURNING id
            """,
            {"taxonomy": taxonomy[0].id, "slug": identifier, "parent": parent_id},
        )
        await term_label(session, term[0].id, name)
        await fetch(
            session,
            """
            INSERT INTO taxonomy_term_mapping (term_id, provider_record_id, confidence)
            VALUES (:term, :record, 1) ON CONFLICT DO NOTHING RETURNING id
            """,
            {"term": term[0].id, "record": record_id},
        )
        spoiler = mapping.spoiler_level(item.get("spoiler"))
        await fetch(
            session,
            """
            INSERT INTO entity_term (entity_id, term_id, observation_id, relevance, spoiler_level)
            VALUES (:entity, :term, :observation, 1, :spoiler)
            ON CONFLICT DO NOTHING RETURNING id
            """,
            {
                "entity": projection.entity_id,
                "term": term[0].id,
                "observation": projection.observation_id,
                "spoiler": spoiler,
            },
        )
        if item.get("lie"):
            await write_facts(
                session,
                projection,
                [
                    mapping.Fact(
                        "vndb-trait-lie",
                        "VNDB Trait Lie",
                        {"trait_id": identifier, "lie": True},
                        "json",
                        f"/traits/{index}/lie",
                        spoiler,
                    )
                ],
            )
