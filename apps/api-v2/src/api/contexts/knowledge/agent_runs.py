"""Durable agent steps and claims backed by explicit source evidence."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


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
        rows = await fetch(
            session,
            "SELECT 1 FROM provider_observation o JOIN entity_representation r "
            "ON r.provider_record_id=o.provider_record_id WHERE o.id=:observation "
            "AND r.entity_id=:entity AND r.is_active LIMIT 1",
            {"observation": context.observation_id, "entity": context.entity_id},
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
    kind: Literal["skill", "tool"] = "skill",
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
           error,retry_count,created_at,started_at)
        VALUES (gen_random_uuid(),:run,
          COALESCE((SELECT max(sequence)+1 FROM agent_step WHERE run_id=:run),0),
          :kind,'running',:skill,:version,:hash,CAST(:input AS jsonb),'',0,now(),now())
        RETURNING id
        """,
        {
            "run": run_id,
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
        rows = await fetch(
            session,
            """
            INSERT INTO ai_claim
              (id,step_id,target_entity_id,claim_type,predicate_slug,proposed_value,
               model_confidence,evidence_strength,status,policy_decision,policy_reason,created_at)
            VALUES (gen_random_uuid(),:step,:entity,:type,:predicate,CAST(:value AS jsonb),
                    :confidence,:strength,'proposed','','',now()) RETURNING id
            """,
            {
                "step": step_id,
                "entity": context.entity_id,
                "type": claim_type,
                "predicate": predicate,
                "value": json.dumps(value),
                "confidence": confidence,
                "strength": evidence_strength,
            },
        )
        claim_id = UUID(str(rows[0].id))
        await fetch(
            session,
            """
            INSERT INTO claim_evidence
              (claim_id,observation_id,artifact_id,locator,excerpt,excerpt_hash,relevance)
            VALUES (:claim,:observation,:artifact,:locator,:excerpt,:hash,1) RETURNING id
            """,
            {
                "claim": claim_id,
                "observation": context.observation_id,
                "artifact": context.artifact_id,
                "locator": locator,
                "excerpt": excerpt[:4000],
                "hash": excerpt_hash,
            },
        )
        return claim_id
