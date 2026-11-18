"""Atomic client-supplied matching proposals with durable inference audit."""

import hashlib
import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from api.contexts.matching.domain import MatchProposal
from api.contexts.presentation.fragments import fetch
from api.worker.session import session_scope


async def submit(
    *,
    candidate_id: UUID,
    decision: str,
    confidence: Decimal,
    reason: str,
    prompt_version: str = "internal-mcp-v1",
) -> dict[str, Any]:
    output = MatchProposal.model_validate(
        {
            "decision": decision,
            "confidence": confidence,
            "reason": reason,
        }
    ).model_dump(mode="json")
    payload = {"candidate_id": str(candidate_id), **output}
    digest = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    async with session_scope() as session:
        if not await fetch(
            session, "SELECT id FROM match_candidate WHERE id=:id FOR UPDATE", {"id": candidate_id}
        ):
            raise LookupError("Match candidate not found.")
        run = (
            await fetch(
                session,
                "INSERT INTO ai_run (id,use_case,provider,model,prompt_version,input_hash,"
                "input_metadata,output,status,error,created_at,started_at,finished_at) "
                "VALUES (gen_random_uuid(),'entity_matching','internal_mcp','mcp_client',:version,"
                ":hash,CAST(:metadata AS jsonb),CAST(:output AS jsonb),"
                "'succeeded','',now(),now(),now()) RETURNING id",
                {
                    "version": prompt_version[:64],
                    "hash": digest,
                    "metadata": json.dumps(
                        {"candidate_id": str(candidate_id), "transport": "stdio"}
                    ),
                    "output": json.dumps(output),
                },
            )
        )[0].id
        proposal = (
            await fetch(
                session,
                "INSERT INTO ai_proposal (id,run_id,match_candidate_id,proposal_type,payload,"
                "confidence,status,policy_reason,created_at) VALUES (gen_random_uuid(),:run,"
                ":candidate,'entity_matching',CAST(:output AS jsonb),:confidence,"
                "'pending',:reason,now()) RETURNING id",
                {
                    "run": run,
                    "candidate": candidate_id,
                    "output": json.dumps(output),
                    "confidence": confidence,
                    "reason": (
                        "Submitted through internal MCP for deterministic policy evaluation; "
                        "no canonical write was performed."
                    ),
                },
            )
        )[0].id
    return {"proposal_id": str(proposal), "status": "pending", "canonical_write": False}
