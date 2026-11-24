"""VNDB source projections with observation-scoped names, artwork and facts."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.names import SourceName
from api.contexts.ingestion import entities, facts, metrics, records
from api.contexts.ingestion import metadata as presentation
from api.contexts.ingestion import observations as ingestion
from api.db import fetch
from api.shared.text import slugify
from api.worker import vndb_mapping as mapping

WORK_MAPPER_VERSION = "vndb-vn-v2"


@dataclass(frozen=True, slots=True)
class Projection:
    entity_id: Any
    record_id: Any
    observation_id: Any


async def ensure_identity(
    session: AsyncSession,
    record_id: Any,
    *,
    kind: str,
    audience: str = "unknown",
    exact_only: bool = True,
) -> Any:
    rows = await fetch(
        session,
        """
        SELECT e.id, e.kind FROM entity_representation AS r
        JOIN entity AS e ON e.id=r.entity_id
        WHERE r.provider_record_id=:record AND r.is_active
          AND (NOT :exact_only OR r.mapping_kind='exact')
        ORDER BY r.created_at, r.id LIMIT 1
        """,
        {"record": record_id, "exact_only": exact_only},
    )
    if rows:
        if rows[0].kind != kind:
            raise ValueError(f"VNDB record {record_id} already represents {rows[0].kind}.")
        entity_id = rows[0].id
    else:
        created = await fetch(
            session,
            """
            INSERT INTO entity
              (id, kind, lifecycle, visibility, audience, spoiler_level, created_at, updated_at)
            VALUES (gen_random_uuid(), :kind, 'active', 'public', :audience, 0, now(), now())
            RETURNING id
            """,
            {"kind": kind, "audience": audience},
        )
        entity_id = created[0].id
    await entities.upsert_representation(session, provider_record_id=record_id, entity_id=entity_id)
    return entity_id


async def record_source(
    session: AsyncSession,
    data: dict[str, Any],
    *,
    namespace: str,
    resource_type: str,
    mapper: str,
    mapper_version: str,
    schema_name: str,
    external_id: str | None = None,
) -> tuple[Any, Any]:
    identifier = external_id if external_id is not None else data["id"]
    recorded = await records.record_payload(
        session,
        provider_slug="vndb",
        namespace_slug=namespace,
        resource_type=resource_type,
        external_id=identifier,
        payload=data,
        canonical_url=f"https://vndb.org/{identifier}",
        schema_version="vndb-kana",
    )
    observation_id = await ingestion.record_observation(
        session,
        provider_record_id=recorded.record_id,
        mapper=mapper,
        mapper_version=mapper_version,
        normalized_data=data,
        schema_name=schema_name,
        schema_version="1",
    )
    return recorded.record_id, observation_id


async def write_names(
    session: AsyncSession, projection: Projection, names: list[SourceName]
) -> None:
    await presentation.record_names(
        session,
        entity_id=projection.entity_id,
        provider_record_id=projection.record_id,
        observation_id=projection.observation_id,
        entries=names,
    )


async def write_media(
    session: AsyncSession,
    projection: Projection,
    image: dict[str, Any],
    *,
    purpose: str,
    sort_order: int = 0,
) -> None:
    url = image.get("url")
    if not isinstance(url, str) or not url:
        return
    asset = await fetch(
        session,
        """
        INSERT INTO media_asset
          (id, url, media_type, safety, spoiler_level, provider_record_id, created_at, updated_at)
        VALUES (gen_random_uuid(), :url, 'image', :safety, 0, :record, now(), now())
        ON CONFLICT (url, provider_record_id) DO UPDATE
          SET media_type=EXCLUDED.media_type, safety=EXCLUDED.safety, updated_at=now()
        RETURNING id
        """,
        {"url": url, "safety": mapping.media_safety(image), "record": projection.record_id},
    )
    await fetch(
        session,
        """
        INSERT INTO entity_media (entity_id, asset_id, purpose, sort_order, observation_id)
        VALUES (:entity, :asset, :purpose, :sort_order, :observation)
        ON CONFLICT DO NOTHING RETURNING id
        """,
        {
            "entity": projection.entity_id,
            "asset": asset[0].id,
            "purpose": purpose,
            "sort_order": sort_order,
            "observation": projection.observation_id,
        },
    )


async def write_links(session: AsyncSession, projection: Projection, data: dict[str, Any]) -> None:
    for item in data.get("extlinks") or []:
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        label = item.get("label") if isinstance(item.get("label"), str) else ""
        slug = slugify(label)
        await fetch(
            session,
            """
            INSERT INTO external_link
              (entity_id, url, provider_record_id, observation_id, label, link_type,
               created_at, updated_at)
            VALUES (:entity, :url, :record, :observation, :label, :link_type, now(), now())
            ON CONFLICT (entity_id, url, provider_record_id, observation_id) DO UPDATE
              SET label=EXCLUDED.label, link_type=EXCLUDED.link_type, updated_at=now()
            RETURNING id
            """,
            {
                "entity": projection.entity_id,
                "url": url,
                "record": projection.record_id,
                "observation": projection.observation_id,
                "label": label[:128],
                "link_type": slug[:64],
            },
        )


async def write_facts(
    session: AsyncSession, projection: Projection, values: list[mapping.Fact]
) -> None:
    for value in values:
        await facts.record_fact(
            session,
            entity_id=projection.entity_id,
            observation_id=projection.observation_id,
            slug=value.slug,
            name=value.name,
            value=value.value,
            value_type=value.value_type,
            json_pointer=value.json_pointer,
            spoiler_level=value.spoiler_level,
        )


async def write_description(
    session: AsyncSession, projection: Projection, data: dict[str, Any]
) -> None:
    description = data.get("description")
    if isinstance(description, str) and description:
        await presentation.upsert_description(
            session,
            entity_id=projection.entity_id,
            provider_record_id=projection.record_id,
            observation_id=projection.observation_id,
            text=description,
        )


async def project_work(session: AsyncSession, vndb_id: str, data: dict[str, Any]) -> Projection:
    """Project the work's own fields before importing its related graph."""
    record_id, observation_id = await record_source(
        session,
        data,
        namespace="vn",
        resource_type="subject",
        mapper="vndb.vn",
        mapper_version=WORK_MAPPER_VERSION,
        schema_name="index.work",
        external_id=vndb_id,
    )
    entity_id = await ensure_identity(
        session, record_id, kind="work", audience=mapping.audience(data)
    )
    projection = Projection(entity_id, record_id, observation_id)
    await entities.ensure_work(session, entity_id=entity_id, work_type="galgame")
    await write_names(session, projection, mapping.work_names(data))
    await write_description(session, projection, data)
    await write_media(session, projection, data.get("image") or {}, purpose="poster")
    for index, image in enumerate(data.get("screenshots") or []):
        await write_media(session, projection, image, purpose="screenshot", sort_order=index)
    await write_links(session, projection, data)
    revision = await fetch(
        session,
        "SELECT r.fetched_at FROM provider_revision AS r JOIN provider_record AS p"
        " ON p.latest_revision_id=r.id WHERE p.id=:record",
        {"record": record_id},
    )
    await metrics.record_metrics(
        session,
        entity_id=entity_id,
        provider_record_id=record_id,
        observed_at=revision[0].fetched_at,
        values={
            "score": data.get("rating"),
            "votes": data.get("votecount"),
            "popularity": data.get("popularity"),
            "playtime-votes": data.get("length_votes"),
        },
    )
    await write_facts(session, projection, mapping.work_facts(data))
    await write_tags(session, projection, data)
    await presentation.ensure_membership(
        session, entity_id=entity_id, work_type="galgame", inclusion_reason="VNDB visual novel"
    )
    return projection


async def write_tags(session: AsyncSession, projection: Projection, data: dict[str, Any]) -> None:
    taxonomy = await fetch(
        session,
        """
        INSERT INTO taxonomy (slug, name, description) VALUES ('vndb-tags', 'VNDB Tags', '')
        ON CONFLICT (slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
        """,
        {},
    )
    for item in data.get("tags") or []:
        identifier, name = item.get("id"), item.get("name")
        if not isinstance(identifier, str) or not isinstance(name, str):
            continue
        record_id = await records.ensure_record(
            session,
            provider_slug="vndb",
            namespace_slug="tag",
            resource_type="taxonomy",
            external_id=identifier,
            canonical_url=f"https://vndb.org/g{identifier.lstrip('g')}",
        )
        term = await fetch(
            session,
            """
            INSERT INTO taxonomy_term (taxonomy_id, slug, parent_id)
            VALUES (:taxonomy, :slug, NULL)
            ON CONFLICT (taxonomy_id, slug) DO UPDATE SET slug=EXCLUDED.slug RETURNING id
            """,
            {"taxonomy": taxonomy[0].id, "slug": identifier},
        )
        await fetch(
            session,
            """
            INSERT INTO taxonomy_term_label (term_id, language, script, text, is_preferred)
            VALUES (:term, 'en', 'Latn', :name, true) ON CONFLICT DO NOTHING RETURNING id
            """,
            {"term": term[0].id, "name": name},
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
            INSERT INTO entity_term (entity_id, term_id, observation_id, relevance, spoiler_level)
            VALUES (:entity, :term, :observation, :relevance, :spoiler)
            ON CONFLICT DO NOTHING RETURNING id
            """,
            {
                "entity": projection.entity_id,
                "term": term[0].id,
                "observation": projection.observation_id,
                "relevance": Decimal(str(item.get("rating") or 1)),
                "spoiler": min(int(item.get("spoiler") or 0), 3),
            },
        )
