"""Durable agent steps and claims backed by explicit source evidence."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index.resolution import cluster_ids
from api.db import fetch

type WriteGuard = Callable[[AsyncSession], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    entity_id: UUID
    run_id: UUID
    observation_id: UUID | None = None
    artifact_id: UUID | None = None

    def __post_init__(self) -> None:
        if (self.observation_id is None) == (self.artifact_id is None):
            raise ValueError("Claim evidence requires exactly one source.")


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def validate_evidence(session: AsyncSession, context: EvidenceContext) -> None:
    if context.observation_id is not None:
        members = await cluster_ids(session, context.entity_id)
        rows = await fetch(
            session,
            "SELECT 1 FROM provider_observation o JOIN entity_representation r "
            "ON r.provider_record_id=o.provider_record_id WHERE o.id=:observation "
            "AND r.entity_id=ANY(:entities) AND r.is_active LIMIT 1",
            {"observation": context.observation_id, "entities": list(members)},
        )
        if not rows:
            raise ValueError("Observation is not an active source for the target entity.")
    else:
        rows = await fetch(
            session,
            "SELECT s.run_id FROM source_artifact a LEFT JOIN tool_invocation t "
            "ON t.id=a.tool_invocation_id LEFT JOIN agent_step s ON s.id=t.step_id "
            "WHERE a.id=:artifact",
            {"artifact": context.artifact_id},
        )
        if not rows or (rows[0].run_id is not None and rows[0].run_id != context.run_id):
            raise ValueError("Artifact does not belong to the current agent run.")


async def create_step(
    session: AsyncSession,
    *,
    run_id: UUID,
    skill: str,
    payload: dict[str, Any],
    kind: Literal["skill", "tool", "model"] = "skill",
    parent_id: UUID | None = None,
    first_sequence: int = 0,
) -> UUID:
    # Serialize sequence allocation for skills sharing the same durable run.
    rows = await fetch(session, "SELECT id FROM agent_run WHERE id=:id FOR UPDATE", {"id": run_id})
    if not rows:
        raise LookupError("Agent run not found.")
    rows = await fetch(
        session,
        """
        INSERT INTO agent_step
          (id,run_id,sequence,kind,status,skill_name,skill_version,input_hash,input,
           error,retry_count,created_at,started_at,parent_id)
        VALUES (gen_random_uuid(),:run,
          COALESCE((SELECT max(sequence)+1 FROM agent_step WHERE run_id=:run),:first),
          :kind,'running',:skill,:version,:hash,CAST(:input AS jsonb),'',0,now(),now(),:parent)
        RETURNING id
        """,
        {
            "run": run_id,
            "parent": parent_id,
            "first": first_sequence,
            "skill": skill,
            "kind": kind,
            "version": "1.0.0" if kind == "skill" else "",
            "hash": payload_hash(payload),
            "input": json.dumps(payload),
        },
    )
    return UUID(str(rows[0].id))


async def finish_step(
    session: AsyncSession, step_id: UUID, output: dict[str, Any] | None, *, error: str = ""
) -> None:
    await fetch(
        session,
        "UPDATE agent_step SET output=CAST(:output AS jsonb),status=:status,error=:error, "
        "finished_at=now() WHERE id=:id RETURNING id",
        {
            "id": step_id,
            "output": json.dumps(output) if output is not None else None,
            "status": "failed" if error else "succeeded",
            "error": error[:4000],
        },
    )


async def record_claim(
    session: AsyncSession,
    *,
    context: EvidenceContext,
    step_id: UUID,
    claim_type: str,
    predicate: str,
    value: dict[str, Any],
    confidence: float,
    evidence_strength: float,
    locator: str,
    excerpt: str,
    excerpt_hash: str,
) -> UUID:
    async with session.begin_nested():
        await validate_evidence(session, context)
        step = await fetch(
            session,
            "SELECT id FROM agent_step WHERE id=:step AND run_id=:run",
            {"step": step_id, "run": context.run_id},
        )
        if not step:
            raise ValueError("Claim step does not belong to the current agent run.")
        claim_id = await create_claim(
            session,
            step_id=step_id,
            entity_id=context.entity_id,
            claim_type=claim_type,
            predicate=predicate,
            value=value,
            confidence=confidence,
            evidence_strength=evidence_strength,
        )
        await add_evidence(
            session,
            claim_id=claim_id,
            observation_id=context.observation_id,
            artifact_id=context.artifact_id,
            locator=locator,
            excerpt=excerpt,
            excerpt_hash=excerpt_hash,
        )
        return claim_id


async def create_claim(
    session: AsyncSession,
    *,
    step_id: UUID,
    entity_id: UUID,
    claim_type: str,
    predicate: str,
    value: dict[str, Any],
    confidence: float,
    evidence_strength: float,
    calibrated_confidence: float | None = None,
) -> UUID:
    rows = await fetch(
        session,
        """
        INSERT INTO ai_claim
          (id,step_id,target_entity_id,claim_type,predicate_slug,proposed_value,
           model_confidence,evidence_strength,calibrated_confidence,status,
           policy_decision,policy_reason,created_at)
        VALUES (gen_random_uuid(),:step,:entity,:type,:predicate,CAST(:value AS jsonb),
                :confidence,:strength,:calibrated,'proposed','','',now()) RETURNING id
        """,
        {
            "step": step_id,
            "entity": entity_id,
            "type": claim_type,
            "predicate": predicate,
            "value": json.dumps(value),
            "confidence": confidence,
            "strength": evidence_strength,
            "calibrated": calibrated_confidence,
        },
    )
    return UUID(str(rows[0].id))


async def add_evidence(
    session: AsyncSession,
    *,
    claim_id: UUID,
    locator: str,
    excerpt: str,
    excerpt_hash: str,
    observation_id: UUID | None = None,
    artifact_id: UUID | None = None,
) -> None:
    if (observation_id is None) == (artifact_id is None):
        raise ValueError("Claim evidence requires exactly one source.")
    await fetch(
        session,
        """
        INSERT INTO claim_evidence
          (claim_id,observation_id,artifact_id,locator,excerpt,excerpt_hash,relevance)
        VALUES (:claim,:observation,:artifact,:locator,:excerpt,:hash,1) RETURNING id
        """,
        {
            "claim": claim_id,
            "observation": observation_id,
            "artifact": artifact_id,
            "locator": locator,
            "excerpt": excerpt[:4000],
            "hash": excerpt_hash,
        },
    )


async def create_run(
    session: AsyncSession,
    *,
    title: str,
    scope: str,
    key: str,
    metadata: dict[str, Any],
    kind: Literal["admin_sync", "admin_enrich", "user_agent", "evaluation"] = "admin_sync",
) -> UUID:
    rows = await fetch(
        session,
        """
        INSERT INTO agent_run
          (id,kind,status,title,idempotency_scope,idempotency_key,trace_id,metadata,checkpoint,
           budget,error,created_at,updated_at)
        VALUES (gen_random_uuid(),:kind,'queued',:title,:scope,:key,'',
                CAST(:metadata AS jsonb),'{}','{}','',now(),now())
        ON CONFLICT (idempotency_scope,idempotency_key) WHERE idempotency_key<>''
        DO UPDATE SET id=agent_run.id RETURNING id
        """,
        {
            "title": title,
            "scope": scope,
            "key": key,
            "metadata": json.dumps(metadata),
            "kind": kind,
        },
    )
    return UUID(str(rows[0].id))


async def recover_interrupted(session: AsyncSession, run_id: UUID, error: str) -> None:
    parameters = {"id": run_id, "error": error}
    for table, column in [("ai_run", "agent_step_id"), ("tool_invocation", "step_id")]:
        await fetch(
            session,
            f"UPDATE {table} SET status='failed',error=:error,finished_at=now() "
            f"WHERE status IN ('queued','running') AND {column} IN "
            "(SELECT id FROM agent_step WHERE run_id=:id) RETURNING id",
            parameters,
        )
    await fetch(
        session,
        "UPDATE agent_step SET status='failed',error=:error,finished_at=now() "
        "WHERE run_id=:id AND status IN ('queued','running') RETURNING id",
        parameters,
    )
