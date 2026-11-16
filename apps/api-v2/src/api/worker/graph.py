"""Contributor subtypes, source credits and evidence-backed entity relations."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


async def ensure_contributor(session: AsyncSession, entity_id: Any, kind: str) -> None:
    await fetch(
        session,
        """
        INSERT INTO contributor (entity_id, kind, created_at, updated_at)
        VALUES (:entity, :kind, now(), now())
        ON CONFLICT (entity_id) DO UPDATE SET kind=EXCLUDED.kind, updated_at=now()
        RETURNING entity_id
        """,
        {"entity": entity_id, "kind": kind},
    )
    if kind == "person":
        await fetch(
            session,
            "INSERT INTO person (contributor_id, created_at, updated_at)"
            " VALUES (:entity, now(), now()) ON CONFLICT DO NOTHING RETURNING contributor_id",
            {"entity": entity_id},
        )
    elif kind == "organization":
        await fetch(
            session,
            "INSERT INTO organization (contributor_id, created_at, updated_at)"
            " VALUES (:entity, now(), now()) ON CONFLICT DO NOTHING RETURNING contributor_id",
            {"entity": entity_id},
        )


async def credit(
    session: AsyncSession,
    work_id: Any,
    contributor_id: Any,
    observation_id: Any,
    *,
    role: str,
    credited_as: str,
) -> None:
    await fetch(
        session,
        """
        INSERT INTO credit
          (work_id, contributor_id, observation_id, role, credited_as, created_at, updated_at)
        VALUES (:work, :contributor, :observation, :role, :name, now(), now())
        ON CONFLICT DO NOTHING RETURNING id
        """,
        {
            "work": work_id,
            "contributor": contributor_id,
            "observation": observation_id,
            "role": role,
            "name": credited_as,
        },
    )


async def relation(
    session: AsyncSession,
    source_id: Any,
    target_id: Any,
    observation_id: Any,
    *,
    relation_type: str,
    json_pointer: str,
    raw_relation: str,
    qualifiers: dict[str, Any] | None = None,
) -> None:
    rows = await fetch(
        session,
        """
        INSERT INTO entity_relation
          (from_entity_id, to_entity_id, relation_type, qualifiers, created_at, updated_at)
        VALUES (:source, :target, :type, CAST(:qualifiers AS jsonb), now(), now())
        ON CONFLICT (from_entity_id, to_entity_id, relation_type)
        DO UPDATE SET relation_type=EXCLUDED.relation_type RETURNING id
        """,
        {
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "qualifiers": json.dumps(qualifiers or {}),
        },
    )
    await fetch(
        session,
        """
        INSERT INTO entity_relation_evidence
          (relation_id, observation_id, json_pointer, raw_relation, created_at, updated_at)
        VALUES (:relation, :observation, :pointer, :raw, now(), now())
        ON CONFLICT DO NOTHING RETURNING id
        """,
        {
            "relation": rows[0].id,
            "observation": observation_id,
            "pointer": json_pointer,
            "raw": raw_relation[:256],
        },
    )
