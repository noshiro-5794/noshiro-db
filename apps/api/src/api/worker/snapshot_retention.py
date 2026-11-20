"""Compact superseded season revisions while retaining referenced observations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

OBSERVATION_REFERENCES = (
    ("ai_proposal", "source_observation_id"),
    ("airing_board", "observation_id"),
    ("airing_event", "observation_id"),
    ("appearance", "observation_id"),
    ("claim_evidence", "observation_id"),
    ("content_rating", "observation_id"),
    ("credit", "observation_id"),
    ("entity_description", "observation_id"),
    ("entity_media", "observation_id"),
    ("entity_name", "observation_id"),
    ("entity_relation_evidence", "observation_id"),
    ("entity_term", "observation_id"),
    ("external_link", "observation_id"),
    ("fact_evidence", "observation_id"),
    ("match_evidence", "observation_id"),
    ("release_work_evidence", "observation_id"),
    ("voice_performance", "observation_id"),
)


async def retain_current(session: AsyncSession, record_id: Any) -> dict[str, int]:
    current = await fetch(
        session,
        "SELECT r.latest_revision_id FROM provider_record r "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id "
        "WHERE r.id=:id AND ns.slug='season' AND p.slug=ANY(:providers) FOR UPDATE OF r",
        {"id": record_id, "providers": ["mal", "anilist"]},
    )
    if not current or current[0].latest_revision_id is None:
        return {"deleted_revisions": 0, "deleted_observations": 0}
    referenced = " OR ".join(
        f"EXISTS (SELECT 1 FROM {table} e WHERE e.{column}=o.id)"
        for table, column in OBSERVATION_REFERENCES
    )
    referenced += (
        " OR EXISTS (SELECT 1 FROM airing_board_entry e WHERE e.source_refs @> "
        "jsonb_build_array(jsonb_build_object('observation_id',o.id::text)))"
    )
    revisions = await fetch(
        session,
        "SELECT v.id FROM provider_revision v WHERE v.record_id=:id "
        "AND v.id<>:latest AND NOT EXISTS ("
        "SELECT 1 FROM mapping_run m JOIN provider_observation o ON o.mapping_run_id=m.id "
        f"WHERE m.revision_id=v.id AND ({referenced}))",
        {"id": record_id, "latest": current[0].latest_revision_id},
    )
    revision_ids = [row.id for row in revisions]
    if not revision_ids:
        return {"deleted_revisions": 0, "deleted_observations": 0}
    params = {"ids": revision_ids}
    await fetch(
        session,
        "DELETE FROM provider_current_observation c USING provider_observation o,mapping_run m "
        "WHERE c.observation_id=o.id AND o.mapping_run_id=m.id AND m.revision_id=ANY(:ids) "
        "RETURNING c.id",
        params,
    )
    observations = await fetch(
        session,
        "DELETE FROM provider_observation o USING mapping_run m "
        "WHERE o.mapping_run_id=m.id AND m.revision_id=ANY(:ids) RETURNING o.id",
        params,
    )
    await fetch(session, "DELETE FROM mapping_run WHERE revision_id=ANY(:ids) RETURNING id", params)
    await fetch(session, "DELETE FROM provider_revision WHERE id=ANY(:ids) RETURNING id", params)
    return {"deleted_revisions": len(revision_ids), "deleted_observations": len(observations)}
