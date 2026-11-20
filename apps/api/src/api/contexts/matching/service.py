"""Durable AI matching runs, proposals and conservative binding policy."""

from __future__ import annotations

import json
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.matching.domain import MatchProposal, bind_allowed, structured_sides
from api.contexts.matching.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from api.db import fetch
from api.shared.ai import complete_json
from api.shared.inference import fail_run, optional_number, start_run
from api.worker.session import session_scope

USE_CASE = "entity_matching"


async def policy_for(session: AsyncSession, version: str) -> Any:
    await fetch(
        session,
        """
        INSERT INTO ai_policy (use_case, policy_version, shadow_mode, minimum_score,
          minimum_margin, minimum_evidence_types, required_evaluation_precision,
          is_enabled, created_at, updated_at)
        VALUES (:use_case, :version, true, 0.9950, 0.0500, 2, 0.9990, true, now(), now())
        ON CONFLICT (use_case) DO NOTHING RETURNING id
    """,
        {"use_case": USE_CASE, "version": version},
    )
    rows = await fetch(
        session, "SELECT * FROM ai_policy WHERE use_case = :use_case", {"use_case": USE_CASE}
    )
    return rows[0]


async def finish_proposal(
    session: AsyncSession, proposal_id: Any, status: str, reason: str
) -> None:
    await fetch(
        session,
        """
        UPDATE ai_proposal SET status = :status, policy_reason = :reason, decided_at = now()
        WHERE id = :id RETURNING id
    """,
        {"id": proposal_id, "status": status, "reason": reason},
    )


async def apply_policy(
    session: AsyncSession,
    candidate: Any,
    policy: Any,
    proposal: MatchProposal,
    proposal_id: Any,
    evidence_types: int,
) -> None:
    if candidate.status != "pending":
        await finish_proposal(
            session, proposal_id, "abstained", "Candidate was already decided by another run."
        )
        return
    ready = False
    if (
        policy.is_enabled
        and not policy.shadow_mode
        and policy.policy_version == candidate.policy_version
    ):
        rows = await fetch(
            session,
            """
            SELECT sample_count, precision FROM ai_evaluation_run
            WHERE use_case = :use_case AND policy_version = :version AND passed
            ORDER BY created_at DESC LIMIT 1
        """,
            {"use_case": USE_CASE, "version": policy.policy_version},
        )
        ready = bool(
            rows
            and rows[0].sample_count > 0
            and rows[0].precision >= policy.required_evaluation_precision
        )
    if not ready:
        await fetch(
            session,
            """
            UPDATE ai_proposal SET policy_reason = :reason WHERE id = :id RETURNING id
        """,
            {
                "id": proposal_id,
                "reason": "Shadow proposal only; policy is disabled, version-mismatched, "
                "or has not passed its production evaluation gate.",
            },
        )
        return
    left = await resolution.cluster_ids(session, candidate.left_entity_id)
    right = await resolution.cluster_ids(session, candidate.right_entity_id)
    types = await fetch(
        session,
        "SELECT entity_id, work_type FROM work WHERE entity_id = ANY(:ids)",
        {"ids": list(left | right)},
    )
    entities = await fetch(
        session,
        "SELECT id, kind FROM entity WHERE id = ANY(:ids)",
        {"ids": [candidate.left_entity_id, candidate.right_entity_id]},
    )
    kinds = {row.id: row.kind for row in entities}
    conflicts = await fetch(
        session,
        """
        SELECT 1 FROM user_library_entry a JOIN user_library_entry b ON a.user_id = b.user_id
        WHERE a.entity_id = :left AND b.entity_id = :right LIMIT 1
    """,
        {"left": candidate.left_entity_id, "right": candidate.right_entity_id},
    )
    allowed = bind_allowed(
        proposal=proposal,
        candidate=candidate,
        policy=policy,
        evidence_types=evidence_types,
        left_kind=kinds.get(candidate.left_entity_id, ""),
        right_kind=kinds.get(candidate.right_entity_id, ""),
        left_types={row.work_type for row in types if row.entity_id in left},
        right_types={row.work_type for row in types if row.entity_id in right},
        library_conflict=bool(conflicts),
    )
    reason = (
        "Passed calibrated conservative auto-bind gate."
        if allowed
        else "Conservative policy abstained because one or more bind gates failed."
    )
    await finish_proposal(session, proposal_id, "accepted" if allowed else "abstained", reason)
    await resolution.decide(
        session,
        candidate_id=candidate.id,
        outcome="bind" if allowed else "abstain",
        reason=reason,
        decided_by="ai_policy",
    )


async def evaluate(candidate_id: str) -> str:
    run_id: UUID | None = None
    try:
        async with session_scope() as session:
            rows = await fetch(
                session,
                "SELECT * FROM match_candidate WHERE id = :id FOR UPDATE",
                {"id": UUID(candidate_id)},
            )
            if not rows:
                raise resolution.CandidateNotFound(candidate_id)
            candidate = rows[0]
            policy = await policy_for(session, candidate.policy_version)
            rows = await fetch(
                session,
                """
                SELECT evidence_type, value, weight FROM match_evidence
                WHERE candidate_id = :id ORDER BY evidence_type
            """,
                {"id": candidate.id},
            )
            evidence = [
                {"evidence_type": row.evidence_type, "value": row.value, "weight": str(row.weight)}
                for row in rows
            ]
            sides = structured_sides(candidate.left_entity_id, evidence)
            payload = {
                "left_entity_id": str(candidate.left_entity_id),
                "right_entity_id": str(candidate.right_entity_id),
                "resolver_score": str(candidate.score),
                "runner_up_margin": str(candidate.runner_up_margin),
                "hard_conflicts": candidate.hard_conflicts,
                "left_work": sides.get("left"),
                "right_work": sides.get("right"),
                "comparison": sides.get("comparison"),
                "evidence": evidence,
            }
            run_id = await start_run(
                payload=payload,
                use_case=USE_CASE,
                prompt_version=PROMPT_VERSION,
                metadata={"candidate_id": str(candidate.id)},
            )
            started = monotonic()
            raw, usage = await complete_json(system=SYSTEM_PROMPT, payload=payload)
            proposal = MatchProposal.model_validate(raw)
            output = proposal.model_dump(mode="json")
            await fetch(
                session,
                """
                UPDATE ai_run SET status = 'succeeded', output = CAST(:output AS jsonb),
                  input_tokens = :input, output_tokens = :output_tokens, cost = :cost,
                  latency_ms = :latency, finished_at = now() WHERE id = :id RETURNING id
            """,
                {
                    "id": run_id,
                    "output": json.dumps(output),
                    "input": optional_number(
                        usage.get("input_tokens", usage.get("prompt_tokens")), integer=True
                    ),
                    "output_tokens": optional_number(
                        usage.get("output_tokens", usage.get("completion_tokens")), integer=True
                    ),
                    "cost": optional_number(usage.get("cost")),
                    "latency": max(0, int((monotonic() - started) * 1000)),
                },
            )
            proposals = await fetch(
                session,
                """
                INSERT INTO ai_proposal (id, run_id, match_candidate_id, proposal_type,
                  payload, confidence, status, policy_reason, created_at)
                VALUES (gen_random_uuid(), :run, :candidate, :type, CAST(:payload AS jsonb),
                  :confidence, 'pending', '', now()) RETURNING id
            """,
                {
                    "run": run_id,
                    "candidate": candidate.id,
                    "type": USE_CASE,
                    "payload": json.dumps(output),
                    "confidence": proposal.confidence,
                },
            )
            proposal_id = proposals[0].id
            await apply_policy(
                session,
                candidate,
                policy,
                proposal,
                proposal_id,
                len({row["evidence_type"] for row in evidence}),
            )
            return str(proposal_id)
    except Exception as error:
        if run_id is not None:
            await fail_run(run_id, error)
        raise
