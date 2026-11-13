"""From a provider record to a canonical entity, and from there to a work row.

Ported from the identity half of `KnowledgeIngestionService`:

* An active representation is the answer to "which entity is this record?"; without one a
  new entity is created. The entity's kind and audience follow the latest mapping — a
  provider that reclassifies a record moves the entity with it.
* A representation is unique per `(record, entity, mapping_kind)`, so re-running an import
  marks the same edge rather than growing a new one.
* The work row is one per entity; its type follows the provider's subject type, falling
  back to ``other`` rather than failing on a type we do not model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

WORK_TYPES = frozenset(
    {
        "anime",
        "galgame",
        "game",
        "manga",
        "light-novel",
        "novel",
        "drama",
        "music",
        "other",
    }
)
EXACT_MAPPING = "exact"
PROVIDER_METHOD = "provider"


@dataclass(frozen=True)
class MappedWork:
    entity_id: Any
    work_id: Any
    created: bool


def work_type_for(subject_type: str | None) -> str:
    return subject_type if subject_type in WORK_TYPES else "other"


async def ensure_entity(
    session: AsyncSession,
    *,
    provider_record_id: Any,
    kind: str,
    audience: str,
) -> tuple[Any, bool]:
    """The entity this record represents, creating one when no mapping exists."""
    rows = await fetch(
        session,
        """
        SELECT e.id, e.kind, e.audience
        FROM entity_representation AS r
        JOIN entity AS e ON e.id = r.entity_id
        WHERE r.provider_record_id = :record AND r.is_active
        ORDER BY r.created_at LIMIT 1
        """,
        {"record": provider_record_id},
    )
    if rows:
        entity = rows[0]
        if entity.kind != kind or entity.audience != audience:
            await fetch(
                session,
                "UPDATE entity SET kind = :kind, audience = :audience,"
                " updated_at = now() WHERE id = :id RETURNING id",
                {"kind": kind, "audience": audience, "id": entity.id},
            )
        return entity.id, False
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
    return created[0].id, True


async def upsert_representation(
    session: AsyncSession,
    *,
    provider_record_id: Any,
    entity_id: Any,
    method: str = PROVIDER_METHOD,
) -> None:
    await fetch(
        session,
        """
        INSERT INTO entity_representation
          (id, provider_record_id, entity_id, mapping_kind, method, confidence,
           is_active, verified_at, created_at, updated_at)
        VALUES (gen_random_uuid(), :record, :entity, :mapping_kind, :method, 1,
                true, NULL, now(), now())
        ON CONFLICT (provider_record_id, entity_id, mapping_kind) WHERE is_active
        DO UPDATE
          SET method = EXCLUDED.method, is_active = true, updated_at = now()
        RETURNING id
        """,
        {
            "record": provider_record_id,
            "entity": entity_id,
            "mapping_kind": EXACT_MAPPING,
            "method": method,
        },
    )


async def ensure_work(session: AsyncSession, *, entity_id: Any, work_type: str) -> Any:
    rows = await fetch(
        session,
        """
        INSERT INTO work
          (entity_id, work_type, popularity, popularity_refreshed_at,
           created_at, updated_at)
        VALUES (:entity, :work_type, 0, NULL, now(), now())
        ON CONFLICT (entity_id) DO UPDATE SET work_type = EXCLUDED.work_type,
                                              updated_at = now()
        RETURNING entity_id
        """,
        {"entity": entity_id, "work_type": work_type},
    )
    return rows[0].entity_id


async def map_work(
    session: AsyncSession,
    *,
    provider_record_id: Any,
    mapped_data: dict[str, Any],
    method: str = PROVIDER_METHOD,
) -> MappedWork:
    """The whole identity step for one provider payload."""
    audience = "adult" if mapped_data.get("nsfw") else "general"
    entity_id, created = await ensure_entity(
        session,
        provider_record_id=provider_record_id,
        kind="work",
        audience=audience,
    )
    await upsert_representation(
        session,
        provider_record_id=provider_record_id,
        entity_id=entity_id,
        method=method,
    )
    work_id = await ensure_work(
        session,
        entity_id=entity_id,
        work_type=work_type_for(mapped_data.get("subject_type")),
    )
    return MappedWork(entity_id=entity_id, work_id=work_id, created=created)


__all__ = [
    "EXACT_MAPPING",
    "PROVIDER_METHOD",
    "WORK_TYPES",
    "MappedWork",
    "ensure_entity",
    "ensure_work",
    "map_work",
    "upsert_representation",
    "work_type_for",
]
