"""Cross-provider identity candidates, newest score first, for staff review."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat

QUERY = """
    SELECT candidate.id, candidate.left_entity_id, candidate.right_entity_id,
           candidate.policy_version, candidate.score, candidate.runner_up_margin,
           candidate.status, candidate.hard_conflicts, candidate.created_at,
           candidate.updated_at,
           (SELECT count(*) FROM match_evidence AS evidence
             WHERE evidence.candidate_id = candidate.id) AS evidence_count,
           proposal.id AS proposal_id, proposal.status AS proposal_status,
           proposal.payload AS proposal_payload,
           proposal.confidence AS proposal_confidence,
           proposal.policy_reason AS proposal_reason,
           proposal.created_at AS proposal_created_at,
           proposal.decided_at AS proposal_decided_at
    FROM match_candidate AS candidate
    LEFT JOIN LATERAL (
        SELECT id, status, payload, confidence, policy_reason, created_at,
               decided_at
        FROM ai_proposal WHERE match_candidate_id = candidate.id
        ORDER BY created_at DESC LIMIT 1
    ) AS proposal ON TRUE
"""


def _proposal(row: Any) -> dict[str, Any] | None:
    if row.proposal_id is None:
        return None
    payload = row.proposal_payload if isinstance(row.proposal_payload, dict) else {}
    return {
        "id": row.proposal_id,
        "status": row.proposal_status,
        "decision": str(payload.get("decision") or ""),
        "confidence": float(row.proposal_confidence)
        if row.proposal_confidence is not None
        else None,
        "policy_reason": row.proposal_reason,
        "created_at": isoformat(row.proposal_created_at),
        "decided_at": isoformat(row.proposal_decided_at),
    }


async def list_candidates(
    session: AsyncSession,
    *,
    status: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    clauses = ["TRUE"]
    params: dict[str, Any] = {}
    if status:
        clauses.append("candidate.status = :status")
        params["status"] = status
    clause = " AND ".join(clauses)
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM match_candidate AS candidate WHERE {clause}",
        params,
    )
    rows = await fetch(
        session,
        QUERY + f" WHERE {clause} ORDER BY candidate.score DESC LIMIT :limit OFFSET :offset",
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "left_entity": str(row.left_entity_id),
            "right_entity": str(row.right_entity_id),
            "policy_version": row.policy_version,
            "score": row.score,
            "runner_up_margin": row.runner_up_margin,
            "status": row.status,
            "hard_conflicts": row.hard_conflicts,
            "evidence_count": int(row.evidence_count),
            "latest_proposal": _proposal(row),
            "created_at": isoformat(row.created_at),
            "updated_at": isoformat(row.updated_at),
        }
        for row in rows
    ]
