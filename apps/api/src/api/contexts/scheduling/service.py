"""Complete tentative board slots from durable web evidence and model proposals."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.scheduling.domain import SlotProposal
from api.contexts.scheduling.prompt import SYSTEM_PROMPT
from api.shared.ai import complete_json
from api.shared.web_search import configured, search
from api.worker.session import session_scope


async def pending_entries(session: AsyncSession, limit: int | None) -> list[Any]:
    query = """
        SELECT entry.*, board.season_key,
          (SELECT text FROM entity_name WHERE entity_id = entry.work_id AND kind = 'original'
           ORDER BY id LIMIT 1) AS title
        FROM airing_board_entry entry JOIN airing_board board ON board.id = entry.board_id
        WHERE board.status = 'active' AND entry.starts_at IS NULL
          AND entry.precision = ANY(:precisions) ORDER BY entry.created_at, entry.id
    """
    params: dict[str, Any] = {"precisions": ["day", "weekday", "unknown"]}
    if limit:
        query += " LIMIT :limit"
        params["limit"] = max(1, int(limit))
    return await fetch(session, query, params)


async def create_run(session: AsyncSession) -> Any:
    rows = await fetch(
        session,
        """
        INSERT INTO agent_run (id, kind, status, title, idempotency_scope, idempotency_key,
          trace_id, metadata, checkpoint, budget, error, created_at, updated_at)
        VALUES (gen_random_uuid(), 'admin_enrich', 'running', 'Airing board schedule completion',
          'board:schedule-completion', '', '', '{}', '{}', '{}', '', now(), now()) RETURNING id
    """,
        {},
    )
    return rows[0].id


async def finish_run(run_id: Any, status: str) -> None:
    async with session_scope() as session:
        await fetch(
            session,
            """
            UPDATE agent_run SET status = :status, finished_at = now(), updated_at = now()
            WHERE id = :id RETURNING id
        """,
            {"id": run_id, "status": status},
        )


async def capture_results(results: list[dict[str, Any]], query: str) -> Any:
    serialized = json.dumps({"results": results}, sort_keys=True, ensure_ascii=False, default=str)
    encoded = serialized.encode()
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            INSERT INTO source_artifact (id, kind, source_url, content_hash, mime_type,
              byte_size, excerpt, object_key, metadata, license_info, fetched_at, created_at)
            VALUES (gen_random_uuid(), 'search_result', :url, :hash, 'application/json',
              :size, :excerpt, '', CAST(:metadata AS jsonb), '', now(), now())
            RETURNING id, content_hash, excerpt
        """,
            {
                "url": str(results[0].get("url") or ""),
                "hash": hashlib.sha256(encoded).hexdigest(),
                "size": len(encoded),
                "excerpt": serialized[:8000],
                "metadata": json.dumps(
                    {"query": query, "tool_name": "web.search", "tool_version": "1.0.0"}
                ),
            },
        )
        return rows[0]


async def persist_result(
    session: AsyncSession,
    *,
    entry: Any,
    run_id: Any,
    sequence: int,
    payload: dict[str, Any],
    parsed: SlotProposal,
    artifact: Any,
    apply: bool,
    now: datetime,
) -> dict[str, Any]:
    output = parsed.model_dump(mode="json")
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    rows = await fetch(
        session,
        """
        INSERT INTO agent_step (id, run_id, sequence, kind, status, skill_name, skill_version,
          input_hash, input, output, error, retry_count, created_at, finished_at)
        VALUES (gen_random_uuid(), :run, :sequence, 'skill', 'succeeded', 'schedule_completion',
          '1.0.0', :hash, CAST(:input AS jsonb), CAST(:output AS jsonb), '', 0, now(), now())
        RETURNING id
    """,
        {
            "run": run_id,
            "sequence": sequence,
            "hash": digest,
            "input": json.dumps(payload),
            "output": json.dumps(output),
        },
    )
    if parsed.decision != "accept":
        return {"bucket": "abstained"}
    step_id = rows[0].id
    rows = await fetch(
        session,
        """
        INSERT INTO ai_claim (id, step_id, target_entity_id, claim_type, predicate_slug,
          proposed_value, model_confidence, evidence_strength, status, policy_decision,
          policy_reason, created_at)
        VALUES (gen_random_uuid(), :step, :entity, 'schedule_completion', 'broadcast-slot',
          CAST(:value AS jsonb), :confidence, 1, 'proposed', '', '', now()) RETURNING id
    """,
        {
            "step": step_id,
            "entity": entry.work_id,
            "value": json.dumps(output),
            "confidence": parsed.confidence,
        },
    )
    claim_id = rows[0].id
    await fetch(
        session,
        """
        INSERT INTO claim_evidence
          (claim_id, artifact_id, locator, excerpt, excerpt_hash, relevance)
        VALUES (:claim, :artifact, 'web.search', :excerpt, :hash, 1) RETURNING id
    """,
        {
            "claim": claim_id,
            "artifact": artifact.id,
            "excerpt": artifact.excerpt,
            "hash": artifact.content_hash,
        },
    )
    applied = False
    if apply and parsed.confidence >= Decimal(os.environ.get("AI_ENRICH_MIN_CONFIDENCE", "0.85")):
        # Re-read under lock so a concurrent board refresh cannot lose source references.
        entries = await fetch(
            session,
            """
            SELECT e.source_refs FROM airing_board_entry e JOIN airing_board b ON b.id = e.board_id
            WHERE e.id = :id AND e.starts_at IS NULL AND b.status = 'active' FOR UPDATE OF e, b
        """,
            {"id": entry.id},
        )
        if entries:
            refs = list(entries[0].source_refs or [])
            refs.append(
                {
                    "provider": "web",
                    "namespace": "schedule-completion",
                    "external_id": "",
                    "claim_id": str(claim_id),
                    "method": "web_evidence",
                }
            )
            await fetch(
                session,
                """
                UPDATE airing_board_entry SET weekday = :weekday, starts_at = :starts,
                  timezone = :zone, duration_minutes = COALESCE(:duration, duration_minutes),
                  precision = 'minute', status = 'scheduled', decision = 'ai',
                  confidence = :confidence,
                  source_refs = CAST(:refs AS jsonb), updated_at = now() WHERE id = :id RETURNING id
            """,
                {
                    "id": entry.id,
                    "weekday": parsed.weekday,
                    "starts": parsed.next_occurrence(now),
                    "zone": parsed.timezone,
                    "duration": parsed.duration_minutes,
                    "confidence": parsed.confidence,
                    "refs": json.dumps(refs),
                },
            )
            await fetch(
                session,
                """
                UPDATE ai_claim SET status = 'accepted', policy_decision = 'auto_apply',
                  policy_reason = 'Confidence cleared the board completion threshold.',
                  decided_at = now()
                WHERE id = :id RETURNING id
            """,
                {"id": claim_id},
            )
            applied = True
    return {"bucket": "accepted", "claim_id": str(claim_id), "applied": applied}


async def run(*, limit: int | None = None, apply: bool = True) -> dict[str, Any]:
    async with session_scope() as session:
        entries = await pending_entries(session, limit)
    summary: dict[str, Any] = {
        "pending": len(entries),
        "searched": 0,
        "accepted": 0,
        "abstained": 0,
        "skipped_no_search": 0,
        "claims": [],
        "applied": 0,
    }
    if not configured():
        summary["skipped_no_search"] = len(entries)
        return summary
    async with session_scope() as session:
        run_id = await create_run(session)
    try:
        for sequence, entry in enumerate(entries):
            title = entry.title or str(entry.work_id)
            query = f"{title} 放送 曜日 時刻 アニメ"
            results = await search(query, max_results=5)
            summary["searched"] += 1
            if not results:
                summary["abstained"] += 1
                continue
            artifact = await capture_results(results, query)
            payload = {
                "work_id": str(entry.work_id),
                "title": title,
                "season_key": entry.season_key,
                "source_refs": entry.source_refs,
                "search_results": results,
            }
            raw, _usage = await complete_json(system=SYSTEM_PROMPT, payload=payload)
            parsed = SlotProposal.model_validate(raw)
            async with session_scope() as session:
                result = await persist_result(
                    session,
                    entry=entry,
                    run_id=run_id,
                    sequence=sequence,
                    payload=payload,
                    parsed=parsed,
                    artifact=artifact,
                    apply=apply,
                    now=datetime.now(UTC),
                )
            summary[result["bucket"]] += 1
            if result.get("claim_id"):
                summary["claims"].append(result["claim_id"])
            summary["applied"] += int(bool(result.get("applied")))
        await finish_run(run_id, "succeeded")
    except Exception:
        await finish_run(run_id, "failed")
        raise
    return summary
