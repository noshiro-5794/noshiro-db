"""Facts: one row per distinct value, with the evidence that supports it.

Ported from `record_fact`. The parts that matter:

* A predicate is shared by every work, so its declared type is a contract: recording a
  string into a predicate that holds numbers is a bug in the mapper, and it is raised
  rather than coerced.
* A fact is unique per ``(entity, predicate, value_hash, language)``, so two observations
  that agree about a value share one fact and each contributes its own evidence.
* Recording a fact rebuilds the resolution decision for that (entity, predicate, language),
  because the selected value may have changed.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.presentation.fragments import fetch

CANDIDATE = "candidate"
UNKNOWN_SAFETY = "unknown"


class PredicateConflict(ValueError):
    """The mapper tried to store a value type a predicate does not hold."""


def value_hash(value: Any) -> str:
    import hashlib

    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


async def _predicate(session: AsyncSession, *, slug: str, name: str, value_type: str) -> Any:
    rows = await fetch(
        session,
        "SELECT id, value_type FROM predicate WHERE slug = :slug",
        {"slug": slug},
    )
    if rows:
        if rows[0].value_type != value_type:
            raise PredicateConflict(
                f"Predicate {slug} expects {rows[0].value_type}, not {value_type}."
            )
        return rows[0].id
    created = await fetch(
        session,
        "INSERT INTO predicate (slug, name, value_type, description, created_at,"
        " updated_at) VALUES (:slug, :name, :value_type, '', now(), now())"
        " RETURNING id",
        {"slug": slug, "name": name, "value_type": value_type},
    )
    return created[0].id


async def record_fact(
    session: AsyncSession,
    *,
    entity_id: Any,
    observation_id: Any,
    slug: str,
    name: str,
    value: Any,
    value_type: str,
    json_pointer: str,
    language: str = "",
    spoiler_level: int = 0,
    safety: str = UNKNOWN_SAFETY,
) -> Any:
    """Store the fact and its evidence, then rebuild the decision that selects it."""
    predicate_id = await _predicate(session, slug=slug, name=name, value_type=value_type)
    digest = value_hash(value)
    inserted = await fetch(
        session,
        """
        INSERT INTO fact
          (id, value, value_hash, language, status, confidence, spoiler_level,
           is_machine_generated, safety, entity_id, predicate_id, created_at, updated_at)
        VALUES (gen_random_uuid(), CAST(:value AS jsonb), :hash, :language,
                :status, 1, :spoiler, false, :safety, :entity, :predicate, now(), now())
        ON CONFLICT (entity_id, predicate_id, value_hash, language) DO NOTHING
        RETURNING id
        """,
        {
            "value": json.dumps(value, ensure_ascii=False, default=str),
            "hash": digest,
            "language": language,
            "status": CANDIDATE,
            "spoiler": spoiler_level,
            "safety": safety,
            "entity": entity_id,
            "predicate": predicate_id,
        },
    )
    if inserted:
        fact_id = inserted[0].id
    else:
        rows = await fetch(
            session,
            "SELECT id FROM fact WHERE entity_id = :entity"
            " AND predicate_id = :predicate AND value_hash = :hash"
            " AND language = :language",
            {
                "entity": entity_id,
                "predicate": predicate_id,
                "hash": digest,
                "language": language,
            },
        )
        fact_id = rows[0].id
    await fetch(
        session,
        """
        INSERT INTO fact_evidence
          (fact_id, observation_id, json_pointer, note, created_at, updated_at)
        VALUES (:fact, :observation, :pointer, '', now(), now())
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        {"fact": fact_id, "observation": observation_id, "pointer": json_pointer},
    )
    await resolution.rebuild_fact(
        session, entity_id=entity_id, predicate_id=predicate_id, language=language
    )
    return fact_id


__all__ = ["CANDIDATE", "UNKNOWN_SAFETY", "PredicateConflict", "record_fact", "value_hash"]
