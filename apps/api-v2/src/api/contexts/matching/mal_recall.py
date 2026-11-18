"""Resumable MAL retrieval and atomic, reviewable candidate materialization."""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.knowledge import agent_loop, agent_runs
from api.contexts.matching.mal_models import (
    ATTEMPT_SCOPE,
    MIN_CONFIDENCE,
    POLICY_VERSION,
    TOOL_NAMES,
    RecallDecision,
    observed_mal_ids,
)
from api.contexts.matching.mal_prompt import SYSTEM_PROMPT
from api.contexts.presentation.fragments import fetch
from api.shared.dispatch import publish
from api.worker import mal_import
from api.worker.providers.mal import MALClient
from api.worker.session import session_scope


@dataclass(frozen=True, slots=True)
class Projection:
    run_id: UUID
    version: datetime


async def own(session: AsyncSession, projection: Projection) -> Any:
    rows = await fetch(
        session,
        "SELECT * FROM agent_run WHERE id=:id AND status='succeeded' "
        "AND updated_at=:version FOR UPDATE",
        {"id": projection.run_id, "version": projection.version},
    )
    if not rows:
        raise agent_loop.ExecutionStopped("MAL recall materialization is no longer owned.")
    return rows[0]


async def bangumi_id(session: AsyncSession, ids: list[UUID]) -> str | None:
    rows = await fetch(
        session,
        "SELECT r.external_id FROM entity_representation rep "
        "JOIN provider_record r ON r.id=rep.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id "
        "WHERE rep.entity_id=ANY(:ids) AND rep.is_active "
        "AND p.slug='bangumi' AND ns.slug='subject' ORDER BY rep.id LIMIT 1",
        {"ids": ids},
    )
    return str(rows[0].external_id) if rows else None


async def attempt_key(session: AsyncSession, root: UUID) -> str:
    return f"bangumi:{await bangumi_id(session, [root]) or root}"


async def context(session: AsyncSession, root: UUID) -> dict[str, Any]:
    cluster = list(await resolution.cluster_ids(session, root))
    names = await fetch(
        session,
        "SELECT text,language,kind FROM entity_name WHERE entity_id=ANY(:ids) "
        "AND text<>'' ORDER BY entity_id,language,kind,id LIMIT 30",
        {"ids": cluster},
    )
    return {
        "entity_id": str(root),
        "bangumi_subject_id": await bangumi_id(session, cluster),
        "names": [{"text": row.text, "language": row.language, "kind": row.kind} for row in names],
    }


async def latest(session: AsyncSession, key: str) -> Any:
    rows = await fetch(
        session,
        "SELECT *,updated_at<clock_timestamp()-make_interval(secs=>:seconds) AS is_stale "
        "FROM agent_run WHERE idempotency_scope=:scope AND idempotency_key=:key "
        "ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
        {
            "scope": ATTEMPT_SCOPE,
            "key": key,
            "seconds": max(60, int(os.environ.get("AI_AGENT_STALE_SECONDS", "3900"))),
        },
    )
    return rows[0] if rows else None


def actionable(row: Any, *, force: bool) -> bool:
    if row is None:
        return True
    if row.status in {"waiting", "paused"}:
        return False
    if row.status == "running":
        return bool(row.is_stale)
    if (row.metadata or {}).get("recall_materializing") and not row.is_stale:
        return False
    if row.status == "succeeded":
        return force or not (row.metadata or {}).get("recall_result")
    return True


async def prepare(root: UUID, *, force: bool) -> UUID | dict[str, Any]:
    async with session_scope() as session:
        key = await attempt_key(session, root)
        await fetch(
            session,
            "SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",
            {"key": f"{ATTEMPT_SCOPE}:{key}"},
        )
        row = await latest(session, key)
        if not actionable(row, force=force):
            result = await agent_loop.read_result(row.id)
            return {
                "root_entity_id": str(root),
                "outcome": "skipped_existing" if row.status == "succeeded" else row.status,
                "run_id": str(row.id),
                "output": result.output,
            }
        if row is not None and row.status in {"queued", "running", "succeeded"} and not force:
            return UUID(str(row.id))
        if row is not None and row.status in {"queued", "running"}:
            return UUID(str(row.id))
        if row is not None:
            await fetch(
                session,
                "UPDATE agent_run SET idempotency_key='',updated_at=clock_timestamp() "
                "WHERE id=:id RETURNING id",
                {"id": row.id},
            )
        details = await context(session, root)
        return await agent_runs.create_run(
            session,
            title=f"MAL recall for Bangumi {details['bangumi_subject_id']}",
            scope=ATTEMPT_SCOPE,
            key=key,
            kind="admin_enrich",
            metadata={"scopes": ["knowledge:read", "mal:read"], "source_root": str(root)},
        )


async def claim_projection(run_id: UUID) -> Projection | None:
    async with session_scope() as session:
        row = (
            await fetch(session, "SELECT * FROM agent_run WHERE id=:id FOR UPDATE", {"id": run_id})
        )[0]
        if row.status != "succeeded" or (row.metadata or {}).get("recall_result"):
            return None
        if (row.metadata or {}).get("recall_materializing"):
            stale = await fetch(
                session,
                "SELECT 1 FROM agent_run WHERE id=:id AND updated_at<clock_timestamp() "
                "-make_interval(secs=>:seconds)",
                {
                    "id": run_id,
                    "seconds": max(60, int(os.environ.get("AI_AGENT_STALE_SECONDS", "3900"))),
                },
            )
            if not stale:
                return None
        version = (
            await fetch(
                session,
                "UPDATE agent_run SET metadata=metadata||CAST(:metadata AS jsonb),"
                "updated_at=clock_timestamp() WHERE id=:id RETURNING updated_at",
                {"id": run_id, "metadata": json.dumps({"recall_materializing": True})},
            )
        )[0].updated_at
    return Projection(run_id, version)


async def allowed_ids(session: AsyncSession, run_id: UUID) -> set[int]:
    messages = await fetch(
        session,
        "SELECT name,content FROM agent_message WHERE run_id=:id AND role='tool' ORDER BY sequence",
        {"id": run_id},
    )
    identifiers = set()
    for message in messages:
        try:
            payload = json.loads(message.content)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            identifiers.update(observed_mal_ids(message.name, payload))
    return identifiers


async def mal_entity(session: AsyncSession, mal_id: int) -> UUID | None:
    rows = await fetch(
        session,
        "SELECT rep.entity_id FROM entity_representation rep "
        "JOIN provider_record r ON r.id=rep.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id "
        "WHERE rep.is_active AND r.status='active' AND p.slug='mal' AND ns.slug='anime' "
        "AND r.external_id=:external ORDER BY rep.id LIMIT 1",
        {"external": str(mal_id)},
    )
    return UUID(str(rows[0].entity_id)) if rows else None


async def fetch_anime(projection: Projection, mal_id: int) -> dict[str, Any]:
    async with session_scope() as session:
        await own(session, projection)
        policy = await fetch(session, "SELECT storage_policy FROM provider WHERE slug='mal'", {})
    client = MALClient()
    client.forbid_storage(forbidden=bool(policy and policy[0].storage_policy == "forbidden"))
    try:
        payload = await asyncio.to_thread(client.fetch_anime, mal_id)
        if payload.get("id") != mal_id:
            raise ValueError("MAL response identifier differs from the selected candidate.")
        return payload
    finally:
        client.close()


async def candidate(
    session: AsyncSession, source: UUID, target: UUID, decision: RecallDecision
) -> UUID:
    left, right = sorted((source, target), key=str)
    created = await fetch(
        session,
        "INSERT INTO match_candidate "
        "(id,left_entity_id,right_entity_id,policy_version,score,runner_up_margin,status,"
        "hard_conflicts,created_at,updated_at) "
        "VALUES (gen_random_uuid(),:left,:right,:policy,:score,0,'pending','[]',now(),now()) "
        "ON CONFLICT (left_entity_id,right_entity_id,policy_version) DO NOTHING RETURNING id",
        {
            "left": left,
            "right": right,
            "policy": POLICY_VERSION,
            "score": Decimal(str(decision.confidence)).quantize(Decimal("0.0001")),
        },
    )
    if not created:
        return UUID(
            str(
                (
                    await fetch(
                        session,
                        "SELECT id FROM match_candidate WHERE left_entity_id=:left "
                        "AND right_entity_id=:right AND policy_version=:policy",
                        {"left": left, "right": right, "policy": POLICY_VERSION},
                    )
                )[0].id
            )
        )
    identifier = UUID(str(created[0].id))
    await fetch(
        session,
        "INSERT INTO match_evidence(candidate_id,evidence_type,value,weight,created_at,updated_at) "
        "VALUES (:candidate,'agent_mal_recall',CAST(:value AS jsonb),:weight,now(),now()) "
        "RETURNING id",
        {
            "candidate": identifier,
            "weight": Decimal(str(decision.confidence)),
            "value": json.dumps(
                {
                    "provider_pair": "bangumi:mal",
                    "mal_id": decision.mal_id,
                    "reason": decision.reason,
                    "policy_version": POLICY_VERSION,
                }
            ),
        },
    )
    return identifier


async def save_result(
    session: AsyncSession, projection: Projection, result: dict[str, Any]
) -> None:
    await own(session, projection)
    await fetch(
        session,
        "UPDATE agent_run SET metadata=(metadata-'recall_materialization_error')"
        "||CAST(:metadata AS jsonb),"
        "updated_at=clock_timestamp() WHERE id=:id RETURNING id",
        {
            "id": projection.run_id,
            "metadata": json.dumps({"recall_materializing": False, "recall_result": result}),
        },
    )


async def materialize(
    root: UUID, projection: Projection, decision: RecallDecision
) -> dict[str, Any]:
    result: dict[str, Any] = {"root_entity_id": str(root), "reason": decision.reason}
    if decision.decision == "not_found":
        result["outcome"] = "not_found"
    elif decision.confidence < MIN_CONFIDENCE:
        result.update(outcome="low_confidence", confidence=str(decision.confidence))
    else:
        async with session_scope() as session:
            await own(session, projection)
            if decision.mal_id not in await allowed_ids(session, projection.run_id):
                result.update(
                    outcome="not_found", reason="Selected MAL id did not appear in a tool result."
                )
            target = await mal_entity(session, decision.mal_id) if decision.mal_id else None
        payload = None
        if "outcome" not in result and target is None:
            assert decision.mal_id is not None
            payload = await fetch_anime(projection, decision.mal_id)
        async with session_scope() as session:
            await own(session, projection)
            if "outcome" not in result:
                if payload is not None:
                    target = await mal_import.import_anime(session, payload)
                assert target is not None
                source = await resolution.resolve(session, root)
                target = await resolution.resolve(session, target)
                identifier = (
                    await candidate(session, source, target, decision) if source != target else None
                )
                result.update(
                    outcome="candidate_created",
                    mal_id=decision.mal_id,
                    candidate_id=str(identifier) if identifier else None,
                    linked_root_id=str(target),
                    confidence=str(decision.confidence),
                )
            await save_result(session, projection, result)
        return result
    async with session_scope() as session:
        await save_result(session, projection, result)
    return result


async def recall_one(root: UUID, *, evaluate: bool = True, force: bool = False) -> dict[str, Any]:
    async with session_scope() as session:
        root = await resolution.resolve(session, root)
        details = await context(session, root)
    prepared = await prepare(root, force=force)
    if isinstance(prepared, dict):
        return prepared
    run = await agent_loop.run(
        prepared,
        system_prompt=SYSTEM_PROMPT,
        user_prompt="Resolve this Bangumi work to a MAL anime id when possible.\n"
        + json.dumps(details, ensure_ascii=False),
        tool_names=TOOL_NAMES,
        output_model=RecallDecision,
        use_case="mal_recall",
    )
    if run.status != "succeeded":
        return {"root_entity_id": str(root), "outcome": run.status, "error": run.error}
    projection = await claim_projection(prepared)
    if projection is None:
        return {"root_entity_id": str(root), "outcome": "already_running", "run_id": str(prepared)}
    try:
        result = await materialize(root, projection, RecallDecision.model_validate(run.output))
    except agent_loop.ExecutionStopped:
        current = await agent_loop.read_result(prepared)
        return {"root_entity_id": str(root), "outcome": current.status, "error": current.error}
    except Exception as error:
        reason = f"{type(error).__name__}: {error}"[:4000]
        async with session_scope() as session:
            await own(session, projection)
            await fetch(
                session,
                "UPDATE agent_run SET metadata=metadata||CAST(:metadata AS jsonb),"
                "updated_at=clock_timestamp() WHERE id=:id RETURNING id",
                {
                    "id": prepared,
                    "metadata": json.dumps(
                        {"recall_materializing": False, "recall_materialization_error": reason}
                    ),
                },
            )
        return {"root_entity_id": str(root), "outcome": "failed", "error": reason}
    if evaluate and result.get("candidate_id"):
        try:
            result["evaluation_dispatched"] = bool(
                await asyncio.to_thread(
                    publish,
                    "apps.ai.tasks.evaluate_match_candidate_task",
                    {"candidate_id": result["candidate_id"]},
                    queue="ai",
                )
            )
        except Exception as error:
            # The existing pending-candidate sweep retries publication after broker outages.
            result.update(evaluation_dispatched=False, evaluation_error=str(error)[:2000])
    return result


async def has_pending_candidate(session: AsyncSession, cluster: list[UUID]) -> bool:
    return bool(
        await fetch(
            session,
            "SELECT 1 FROM match_candidate c WHERE c.status='pending' AND EXISTS ("
            "SELECT 1 FROM entity_representation rep "
            "JOIN provider_record r ON r.id=rep.provider_record_id "
            "JOIN provider_namespace ns ON ns.id=r.namespace_id "
            "JOIN provider p ON p.id=ns.provider_id "
            "WHERE rep.is_active AND p.slug='mal' AND ns.slug='anime' AND "
            "((c.left_entity_id=ANY(:ids) AND rep.entity_id=c.right_entity_id) OR "
            "(c.right_entity_id=ANY(:ids) AND rep.entity_id=c.left_entity_id))) LIMIT 1",
            {"ids": cluster},
        )
    )


async def run_missing(
    *, limit: int = 10, evaluate: bool = True, force: bool = False
) -> dict[str, Any]:
    async with session_scope() as session:
        entries = await fetch(
            session,
            "SELECT e.work_id FROM airing_board_entry e WHERE e.board_id=("
            "SELECT id FROM airing_board WHERE status='active' ORDER BY created_at,id LIMIT 1) "
            "AND e.source_refs->0->>'provider'='bangumi' ORDER BY e.id",
            {},
        )
    results: list[dict[str, Any]] = []
    seen = set()
    for entry in entries:
        if len(results) >= max(1, int(limit)):
            break
        async with session_scope() as session:
            root = await resolution.resolve(session, entry.work_id)
            if root in seen:
                continue
            seen.add(root)
            cluster = list(await resolution.cluster_ids(session, root))
            if not await fetch(
                session,
                "SELECT 1 FROM work WHERE entity_id=ANY(:ids) AND work_type='anime' LIMIT 1",
                {"ids": cluster},
            ):
                continue
            if await has_pending_candidate(session, cluster):
                continue
            if not actionable(await latest(session, await attempt_key(session, root)), force=force):
                continue
        result = await recall_one(root, evaluate=evaluate, force=force)
        if result.get("outcome") not in {
            "skipped_existing",
            "already_running",
            "running",
            "queued",
            "paused",
            "waiting",
        }:
            results.append(result)
    return {"policy_version": POLICY_VERSION, "processed": len(results), "results": results}
