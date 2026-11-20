"""Rotating administrative application of evidence-qualified matching proposals."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.work_families import are_bindable
from api.contexts.index import resolution
from api.contexts.matching.service import finish_proposal
from api.contexts.presentation.fragments import fetch

TASK = "match_apply_rotation"
SHARD = "pending"
MIN_SCORE = Decimal("0.9500")
MIN_CONFIDENCE = Decimal("0.9200")
PENDING = """
    FROM ai_proposal p JOIN match_candidate c ON c.id = p.match_candidate_id
    JOIN ai_run r ON r.id = p.run_id
    JOIN entity l ON l.id = c.left_entity_id JOIN entity rt ON rt.id = c.right_entity_id
    WHERE p.status = 'pending' AND c.status = 'pending' AND r.status = 'succeeded'
"""
COLUMNS = """
    p.id AS proposal_id, p.payload, p.confidence, c.id AS candidate_id, c.score,
    c.left_entity_id, c.right_entity_id, c.hard_conflicts,
    l.kind AS left_kind, rt.kind AS right_kind
"""


async def read_window(session: AsyncSession, cursor: int, batch: int) -> tuple[list[Any], int]:
    count = await fetch(session, "SELECT count(*) AS total " + PENDING, {})
    rows = await fetch(
        session,
        "SELECT " + COLUMNS + PENDING + " ORDER BY p.created_at, p.id LIMIT :limit OFFSET :cursor",
        {"limit": batch, "cursor": cursor},
    )
    return rows, int(count[0].total)


async def gate_reasons(session: AsyncSession, proposal: Any) -> list[str]:
    reasons = []
    decision = proposal.payload.get("decision")
    if decision != "bind":
        reasons.append(f"ai_decision={decision!r}")
    if proposal.confidence < MIN_CONFIDENCE:
        reasons.append("confidence_below_threshold")
    if proposal.score < MIN_SCORE:
        reasons.append("candidate_score_below_threshold")
    if proposal.hard_conflicts:
        reasons.append("hard_conflicts")
    if proposal.left_kind != proposal.right_kind:
        reasons.append("entity_kind_mismatch")
    left = await resolution.cluster_ids(session, proposal.left_entity_id)
    right = await resolution.cluster_ids(session, proposal.right_entity_id)
    rows = await fetch(
        session,
        "SELECT entity_id, work_type FROM work WHERE entity_id = ANY(:ids)",
        {"ids": list(left | right)},
    )
    left_types = {row.work_type for row in rows if row.entity_id in left}
    right_types = {row.work_type for row in rows if row.entity_id in right}
    if not are_bindable(left_types, right_types):
        reasons.append("work_family_mismatch")
    rows = await fetch(
        session,
        "SELECT premiered_on FROM anime_profile WHERE work_id = ANY(:ids) ORDER BY work_id",
        {"ids": [proposal.left_entity_id, proposal.right_entity_id]},
    )
    years = [row.premiered_on.year for row in rows if row.premiered_on is not None]
    if len(years) == 2 and abs(years[0] - years[1]) > 1:
        reasons.append("release_year_conflict")
    rows = await fetch(
        session,
        """
        SELECT 1 FROM user_library_entry a JOIN user_library_entry b ON a.user_id = b.user_id
        WHERE a.entity_id = :left AND b.entity_id = :right LIMIT 1
    """,
        {"left": proposal.left_entity_id, "right": proposal.right_entity_id},
    )
    if rows:
        reasons.append("conflicting_user_library")
    return reasons


async def decide(session: AsyncSession, proposal: Any, eligible: bool) -> str:
    candidates = await fetch(
        session,
        "SELECT status FROM match_candidate WHERE id = :id FOR UPDATE",
        {"id": proposal.candidate_id},
    )
    if not candidates or candidates[0].status != "pending":
        await finish_proposal(
            session,
            proposal.proposal_id,
            "abstained",
            "Candidate was already decided by another run.",
        )
        return "already_decided"
    left = await resolution.resolve(session, proposal.left_entity_id)
    right = await resolution.resolve(session, proposal.right_entity_id)
    if left == right:
        await resolution.decide(
            session,
            candidate_id=proposal.candidate_id,
            outcome="abstain",
            decided_by="admin_batch",
            reason="Already bound by another rule.",
        )
        await finish_proposal(
            session, proposal.proposal_id, "accepted", "Pair already bound by another rule."
        )
        return "already_bound"
    if eligible:
        reason = (
            f"Admin conservative batch: AI bind at {proposal.confidence} "
            f"confidence on candidate score {proposal.score}."
        )
        try:
            await resolution.decide(
                session,
                candidate_id=proposal.candidate_id,
                outcome="bind",
                decided_by="admin_batch",
                reason=reason,
            )
        except resolution.UserLibraryConflict:
            reason = "Admin conservative batch: blocked by conflicting user library entries."
            await resolution.decide(
                session,
                candidate_id=proposal.candidate_id,
                outcome="abstain",
                decided_by="admin_batch",
                reason=reason,
            )
            await finish_proposal(session, proposal.proposal_id, "abstained", reason)
            return "blocked"
        await finish_proposal(session, proposal.proposal_id, "accepted", reason)
        return "accepted"
    reason = "Admin conservative batch abstained."
    await resolution.decide(
        session,
        candidate_id=proposal.candidate_id,
        outcome="abstain",
        decided_by="admin_batch",
        reason=reason,
    )
    await finish_proposal(session, proposal.proposal_id, "abstained", reason)
    return "abstained"


async def apply_proposals(
    session: AsyncSession, *, limit: int = 200, apply: bool = False, abstain_ineligible: bool = True
) -> dict[str, Any]:
    if apply:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": f"{TASK}:{SHARD}"},
        )
    state = await fetch(
        session,
        "SELECT current_id FROM sync_state WHERE task_name = :task AND shard = :shard",
        {"task": TASK, "shard": SHARD},
    )
    cursor = int(state[0].current_id) if state else 0
    proposals, total = await read_window(session, cursor, max(1, int(limit)))
    wrapped = not proposals and cursor > 0
    if wrapped:
        cursor = 0
        proposals, total = await read_window(session, cursor, max(1, int(limit)))
    summary: dict[str, Any] = {
        "processed": 0,
        "would_bind": 0,
        "accepted": 0,
        "abstained": 0,
        "already_bound": 0,
        "blocked": 0,
        "deferred": 0,
        "errors": [],
        "rows": [],
        "cursor_before": cursor,
        "cursor_after": cursor,
        "pending": total,
        "completed_pass": wrapped,
    }
    for proposal in proposals:
        reasons = await gate_reasons(session, proposal)
        eligible = not reasons
        summary["processed"] += 1
        summary["would_bind"] += int(eligible)
        summary["rows"].append(
            {
                "proposal_id": str(proposal.proposal_id),
                "candidate_id": str(proposal.candidate_id),
                "decision": proposal.payload.get("decision"),
                "confidence": str(proposal.confidence),
                "score": str(proposal.score),
                "eligible": eligible,
                "reasons": reasons,
            }
        )
        if not apply:
            continue
        if not eligible and not abstain_ineligible:
            summary["deferred"] += 1
            continue
        try:
            async with session.begin_nested():
                outcome = await decide(session, proposal, eligible)
            if outcome in {"already_bound", "blocked", "already_decided"}:
                summary[outcome] = summary.get(outcome, 0) + 1
            else:
                summary["accepted" if eligible else "abstained"] += 1
        except Exception as error:
            summary["errors"].append(
                {"proposal_id": str(proposal.proposal_id), "error": str(error)[:2000]}
            )
    if apply and proposals:
        survivors = await fetch(
            session,
            """
            SELECT count(*) AS total FROM ai_proposal WHERE id = ANY(:ids) AND status = 'pending'
        """,
            {"ids": [row.proposal_id for row in proposals]},
        )
        surviving = int(survivors[0].total)
        summary["cursor_after"] = cursor + surviving
        await fetch(
            session,
            """
            INSERT INTO sync_state
              (task_name, shard, current_id, end_id, status, fail_count, updated_at)
            VALUES (:task, :shard, :cursor, :total, 'running', 0, now())
            ON CONFLICT (task_name, shard) DO UPDATE SET current_id = EXCLUDED.current_id,
              end_id = EXCLUDED.end_id, status = EXCLUDED.status, updated_at = now() RETURNING id
        """,
            {
                "task": TASK,
                "shard": SHARD,
                "cursor": summary["cursor_after"],
                "total": max(0, total - (len(proposals) - surviving)),
            },
        )
    return summary
