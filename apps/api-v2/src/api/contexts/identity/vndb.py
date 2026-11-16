"""Reconcile explicit Bangumi-to-VNDB identifiers through auditable decisions."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.presentation.fragments import fetch

POLICY = "official-cross-id-v1"


async def reconcile(session: AsyncSession, entity_id: Any, vndb_id: str) -> Any:
    rows = await fetch(
        session,
        """
        SELECT DISTINCT f.entity_id, o.id AS observation_id
        FROM fact AS f JOIN predicate AS p ON p.id=f.predicate_id
        JOIN fact_evidence AS e ON e.fact_id=f.id
        JOIN provider_observation AS o ON o.id=e.observation_id
        JOIN provider_record AS r ON r.id=o.provider_record_id
        JOIN provider_namespace AS ns ON ns.id=r.namespace_id
        JOIN provider AS source ON source.id=ns.provider_id
        JOIN provider_current_observation AS current
          ON current.observation_id=o.id AND current.provider_record_id=r.id
        WHERE p.slug='external-id-vndb' AND f.value=CAST(:value AS jsonb)
          AND source.slug='bangumi' AND r.status='active'
        ORDER BY f.entity_id, o.id
        """,
        {"value": json.dumps(vndb_id.lower())},
    )
    for row in rows:
        await bind_pair(session, row.entity_id, entity_id, row.observation_id, vndb_id.lower())
    return await resolution.resolve(session, entity_id)


async def bind_pair(
    session: AsyncSession, bangumi_id: Any, vndb_id: Any, observation_id: Any, external_id: str
) -> None:
    bangumi_root = await resolution.resolve(session, bangumi_id)
    vndb_root = await resolution.resolve(session, vndb_id)
    if bangumi_root == vndb_root:
        return
    entities = await fetch(
        session,
        "SELECT e.id, e.kind, w.work_type FROM entity e LEFT JOIN work w ON w.entity_id=e.id"
        " WHERE e.id=ANY(:ids) ORDER BY e.id FOR UPDATE OF e",
        {"ids": [bangumi_root, vndb_root]},
    )
    by_id = {row.id: row for row in entities}
    left, right = by_id[bangumi_root], by_id[vndb_root]
    compatible = (
        left.kind == right.kind == "work"
        and left.work_type in {"galgame", "game"}
        and right.work_type == "galgame"
    )
    if compatible:
        await fetch(
            session,
            "UPDATE work SET work_type='galgame', updated_at=now()"
            " WHERE entity_id=:id RETURNING entity_id",
            {"id": bangumi_root},
        )
    a, b = sorted((bangumi_root, vndb_root), key=str)
    candidate = (
        await fetch(
            session,
            """
        INSERT INTO match_candidate
          (id, left_entity_id, right_entity_id, score, runner_up_margin, policy_version,
           status, hard_conflicts, created_at, updated_at)
        VALUES (gen_random_uuid(), :a, :b, 1, 1, :policy, 'pending',
                CAST(:conflicts AS jsonb), now(), now())
        ON CONFLICT (left_entity_id, right_entity_id, policy_version)
        DO UPDATE SET policy_version=EXCLUDED.policy_version RETURNING id, status
        """,
            {
                "a": a,
                "b": b,
                "policy": POLICY,
                "conflicts": json.dumps([] if compatible else ["entity_type"]),
            },
        )
    )[0]
    await fetch(
        session,
        """
        INSERT INTO match_evidence
          (candidate_id, evidence_type, observation_id, value, weight, created_at, updated_at)
        VALUES (:candidate, 'official_external_id', :observation, CAST(:value AS jsonb),
                1, now(), now()) ON CONFLICT DO NOTHING RETURNING id
        """,
        {
            "candidate": candidate.id,
            "observation": observation_id,
            "value": json.dumps({"provider": "vndb", "external_id": external_id}),
        },
    )
    if candidate.status != "pending":
        return
    if not compatible:
        await resolution.decide(
            session,
            candidate_id=candidate.id,
            outcome="abstain",
            decided_by="official_external_id",
            reason="Official identifier conflicts with canonical entity types.",
        )
        return
    try:
        await resolution.decide(
            session,
            candidate_id=candidate.id,
            outcome="bind",
            decided_by="official_external_id",
            reason=f"Bangumi explicitly references VNDB {external_id}.",
        )
    except resolution.ResolutionError as error:
        await resolution.decide(
            session,
            candidate_id=candidate.id,
            outcome="abstain",
            decided_by="official_external_id",
            reason=f"Verified identifier could not be bound safely: {error}",
        )
