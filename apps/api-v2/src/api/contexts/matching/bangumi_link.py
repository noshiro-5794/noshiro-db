"""Audited external-search proposals for MAL works missing a Bangumi identity."""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.knowledge import agent_runs, artifacts
from api.contexts.matching.bangumi_models import (
    ATTEMPT_SCOPE,
    MIN_CONFIDENCE,
    POLICY_VERSION,
    SEARCH_LIMIT,
    LinkDecision,
    search_queries,
)
from api.contexts.matching.bangumi_prompt import PROMPT_VERSION, SYSTEM_PROMPT
from api.contexts.presentation.fragments import fetch
from api.shared import inference
from api.shared.ai import complete_json
from api.worker import bangumi_episodes, incremental_tasks, provider_search
from api.worker.providers.bangumi import BangumiClient
from api.worker.session import session_scope
from api.worker.subject_import import import_subject

USE_CASE = "bangumi_link_search"


class AttemptStopped(RuntimeError):
    """The current attempt was paused, cancelled or replaced."""


@dataclass(frozen=True, slots=True)
class Attempt:
    root_id: UUID
    run_id: UUID
    version: datetime
    names: list[str]
    mal_ids: list[int]


async def own(session: AsyncSession, attempt: Attempt) -> Any:
    rows = await fetch(
        session,
        "SELECT * FROM agent_run WHERE id=:id AND status='running' "
        "AND updated_at=:version FOR UPDATE",
        {"id": attempt.run_id, "version": attempt.version},
    )
    if not rows:
        raise AttemptStopped("Bangumi link attempt is no longer owned by this invocation.")
    return rows[0]


async def needs_link(session: AsyncSession, root_id: UUID) -> bool:
    cluster = list(await resolution.cluster_ids(session, root_id))
    if not await fetch(
        session, "SELECT 1 FROM work WHERE entity_id=:id AND work_type='anime'", {"id": root_id}
    ):
        return False
    if await fetch(
        session,
        "SELECT 1 FROM entity_representation rep "
        "JOIN provider_record r ON r.id=rep.provider_record_id "
        "JOIN provider_namespace ns ON ns.id=r.namespace_id "
        "JOIN provider p ON p.id=ns.provider_id "
        "WHERE rep.entity_id=ANY(:ids) AND rep.is_active AND r.status='active' "
        "AND p.slug='bangumi' AND ns.slug='subject' LIMIT 1",
        {"ids": cluster},
    ):
        return False
    return not await fetch(
        session,
        "SELECT 1 FROM match_candidate WHERE status='pending' AND policy_version<>:policy "
        "AND (left_entity_id=ANY(:ids) OR right_entity_id=ANY(:ids)) LIMIT 1",
        {"ids": cluster, "policy": POLICY_VERSION},
    )


async def prepare(root_id: UUID, *, force: bool) -> Attempt | dict[str, Any]:
    async with session_scope() as session:
        root_id = await resolution.resolve(session, root_id)
        cluster = list(await resolution.cluster_ids(session, root_id))
        mal_ids = sorted(
            int(row.external_id)
            for row in await fetch(
                session,
                "SELECT r.external_id FROM entity_representation rep "
                "JOIN provider_record r ON r.id=rep.provider_record_id "
                "JOIN provider_namespace ns ON ns.id=r.namespace_id "
                "JOIN provider p ON p.id=ns.provider_id "
                "WHERE rep.entity_id=ANY(:ids) AND rep.is_active AND r.status='active' "
                "AND p.slug='mal' AND ns.slug='anime'",
                {"ids": cluster},
            )
        )
        anchor = mal_ids[0] if mal_ids else str(root_id).replace("-", "")
        key = f"mal:{anchor}"
        await fetch(
            session,
            "SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",
            {"key": f"{ATTEMPT_SCOPE}:{key}"},
        )
        run_id = await agent_runs.create_run(
            session,
            title=f"Bangumi link for MAL {mal_ids[0] if mal_ids else None}",
            scope=ATTEMPT_SCOPE,
            key=key,
            metadata={
                "source_root": str(root_id),
                "mal_ids": mal_ids,
                "scopes": ["bangumi:search"],
            },
        )
        row = (
            await fetch(
                session,
                "SELECT status,updated_at<clock_timestamp()-make_interval(secs=>:seconds) "
                "AS is_stale FROM agent_run WHERE id=:id FOR UPDATE",
                {
                    "id": run_id,
                    "seconds": max(
                        60, int(os.environ.get("BANGUMI_LINK_ATTEMPT_STALE_SECONDS", "3900"))
                    ),
                },
            )
        )[0]
        if row.status in {"waiting", "paused"} or (row.status == "running" and not row.is_stale):
            return {
                "root_entity_id": str(root_id),
                "outcome": "already_running",
                "attempt_id": str(run_id),
            }
        if row.status in {"succeeded", "cancelled"} and not force:
            return {
                "root_entity_id": str(root_id),
                "outcome": "skipped_existing",
                "attempt_id": str(run_id),
            }
        if row.status == "running":
            await recover_interrupted(session, run_id)
        version = (
            await fetch(
                session,
                "UPDATE agent_run SET status='running',started_at=COALESCE(started_at,now()),"
                "finished_at=NULL,error='',updated_at=clock_timestamp() "
                "WHERE id=:id RETURNING updated_at",
                {"id": run_id},
            )
        )[0].updated_at
        names = []
        seen = set()
        for row in await fetch(
            session,
            "SELECT text FROM entity_name WHERE entity_id=ANY(:ids) AND text<>'' ORDER BY id",
            {"ids": cluster},
        ):
            normalized = " ".join(row.text.strip().split())
            if normalized and normalized.casefold() not in seen:
                seen.add(normalized.casefold())
                names.append(normalized[:512])
                if len(names) >= 16:
                    break
        return Attempt(root_id, run_id, version, names, mal_ids)


async def recover_interrupted(session: AsyncSession, run_id: UUID) -> None:
    parameters = {"id": run_id, "error": "Bangumi link attempt was interrupted before completion."}
    for table, column in [("ai_run", "agent_step_id"), ("tool_invocation", "step_id")]:
        await fetch(
            session,
            f"UPDATE {table} SET status='failed',error=:error,finished_at=now() "
            f"WHERE status='running' AND {column} IN "
            "(SELECT id FROM agent_step WHERE run_id=:id AND status='running') RETURNING id",
            parameters,
        )
    await fetch(
        session,
        "UPDATE agent_step SET status='failed',error=:error,finished_at=now() "
        "WHERE run_id=:id AND status='running' RETURNING id",
        parameters,
    )


async def finish(attempt: Attempt, outcome: str, metadata: dict[str, Any]) -> dict[str, Any]:
    async with session_scope() as session:
        row = await own(session, attempt)
        details = {**(row.metadata or {}), **metadata, "outcome": outcome}
        await fetch(
            session,
            "UPDATE agent_run SET status='succeeded',metadata=CAST(:metadata AS jsonb),"
            "finished_at=now(),updated_at=clock_timestamp() WHERE id=:id RETURNING id",
            {"id": attempt.run_id, "metadata": json.dumps(details)},
        )
    return {
        "root_entity_id": str(attempt.root_id),
        "outcome": outcome,
        "attempt_id": str(attempt.run_id),
        **metadata,
    }


async def failed(attempt: Attempt, error: Exception) -> dict[str, Any]:
    reason = f"{type(error).__name__}: {error}"[:4000]
    async with session_scope() as session:
        try:
            row = await own(session, attempt)
        except AttemptStopped:
            current = await fetch(
                session, "SELECT status,error FROM agent_run WHERE id=:id", {"id": attempt.run_id}
            )
            return {
                "root_entity_id": str(attempt.root_id),
                "outcome": current[0].status if current else "cancelled",
                "attempt_id": str(attempt.run_id),
                "error": current[0].error if current else reason,
            }
        details = {**(row.metadata or {}), "outcome": "failed", "error": reason}
        await fetch(
            session,
            "UPDATE agent_run SET status='failed',metadata=CAST(:metadata AS jsonb),error=:error,"
            "finished_at=now(),updated_at=clock_timestamp() WHERE id=:id RETURNING id",
            {"id": attempt.run_id, "metadata": json.dumps(details), "error": reason},
        )
    return {
        "root_entity_id": str(attempt.root_id),
        "outcome": "failed",
        "attempt_id": str(attempt.run_id),
        "error": reason,
    }


async def select_subject(attempt: Attempt, candidates: list[dict[str, Any]]) -> LinkDecision:
    payload = {
        "source": {
            "kind": "anime",
            "mal_id": attempt.mal_ids[0] if attempt.mal_ids else None,
            "names": attempt.names,
            "entity_id": str(attempt.root_id),
        },
        "candidates": candidates,
        "rule": (
            "Select the single Bangumi subject that is the same anime as the source work. "
            "Never invent a subject_id that is not in the candidate list. Only choose found "
            "when the match is highly confident (title and broadcast date/season agree); "
            "otherwise return not_found."
        ),
    }
    async with session_scope() as session:
        await own(session, attempt)
        step = await agent_runs.create_step(
            session, run_id=attempt.run_id, skill="", payload={"use_case": USE_CASE}, kind="model"
        )
    inference_id = await inference.start_run(
        payload=payload,
        use_case=USE_CASE,
        prompt_version=PROMPT_VERSION,
        metadata={"root_entity_id": str(attempt.root_id)},
        agent_step_id=step,
    )
    started = monotonic()
    try:
        raw, usage = await complete_json(system=SYSTEM_PROMPT, payload=payload)
        decision = LinkDecision.model_validate(raw).constrained({item["id"] for item in candidates})
        output = decision.model_dump(mode="json")
        await inference.finish_run(
            inference_id, output, usage, latency_ms=max(0, int((monotonic() - started) * 1000))
        )
        async with session_scope() as session:
            await own(session, attempt)
            await agent_runs.finish_step(session, step, output)
        return decision
    except Exception as error:
        await inference.fail_run(inference_id, error)
        async with session_scope() as session:
            await agent_runs.finish_step(
                session, step, None, error=f"{type(error).__name__}: {error}"[:4000]
            )
        raise


async def sync_subject(attempt: Attempt, subject_id: int) -> tuple[UUID, bool]:
    async with session_scope() as session:
        await own(session, attempt)
        policy = await fetch(
            session, "SELECT storage_policy FROM provider WHERE slug='bangumi'", {}
        )
    client = BangumiClient()
    client.forbid_storage(forbidden=bool(policy and policy[0].storage_policy == "forbidden"))
    try:
        payload = await asyncio.to_thread(client.fetch_subject, subject_id)
        async with session_scope() as session:
            await own(session, attempt)
            entity_id = await import_subject(session, payload)
        try:
            episodes = await asyncio.to_thread(
                incremental_tasks.fetch_source, client, "episodes", subject_id
            )
            async with session_scope() as session:
                await own(session, attempt)
                await bangumi_episodes.import_episodes(
                    session, entity_id, str(subject_id), episodes
                )
            return entity_id, True
        except AttemptStopped:
            raise
        except Exception:
            return entity_id, False
    finally:
        client.close()


async def create_candidate(
    session: AsyncSession, attempt: Attempt, target_id: UUID, decision: LinkDecision
) -> UUID | None:
    source = await resolution.resolve(session, attempt.root_id)
    target = await resolution.resolve(session, target_id)
    types = await fetch(
        session, "SELECT work_type FROM work WHERE entity_id=ANY(:ids)", {"ids": [source, target]}
    )
    if len(types) != 2 or any(row.work_type != "anime" for row in types):
        return None
    left, right = sorted((source, target), key=str)
    created = await fetch(
        session,
        "INSERT INTO match_candidate "
        "(id,left_entity_id,right_entity_id,policy_version,score,runner_up_margin,status,"
        "hard_conflicts,created_at,updated_at) "
        "VALUES (gen_random_uuid(),:left,:right,:policy,:score,0.1000,'pending','[]',now(),now()) "
        "ON CONFLICT (left_entity_id,right_entity_id,policy_version) DO NOTHING RETURNING id",
        {"left": left, "right": right, "policy": POLICY_VERSION, "score": decision.confidence},
    )
    if not created:
        existing = await fetch(
            session,
            "SELECT id,status FROM match_candidate WHERE left_entity_id=:left "
            "AND right_entity_id=:right AND policy_version=:policy",
            {"left": left, "right": right, "policy": POLICY_VERSION},
        )
        return UUID(str(existing[0].id)) if existing and existing[0].status == "pending" else None
    identifier = UUID(str(created[0].id))
    await fetch(
        session,
        "INSERT INTO match_evidence(candidate_id,evidence_type,value,weight,created_at,updated_at) "
        "VALUES (:candidate,'provider_search',CAST(:value AS jsonb),:score,now(),now()) "
        "RETURNING id",
        {
            "candidate": identifier,
            "score": decision.confidence,
            "value": json.dumps(
                {
                    "provider": "bangumi",
                    "subject_id": decision.subject_id,
                    "source_url": f"https://bgm.tv/subject/{decision.subject_id}",
                    "matched_names": attempt.names[:8],
                    "policy_version": POLICY_VERSION,
                }
            ),
        },
    )
    return identifier


async def attempt(root_id: UUID, *, apply: bool = False, force: bool = False) -> dict[str, Any]:
    prepared = await prepare(root_id, force=force)
    if isinstance(prepared, dict):
        return prepared

    async def guard(session: AsyncSession) -> None:
        await own(session, prepared)

    try:
        queries = search_queries(prepared.names)
        candidates = []
        seen = set()
        for query in queries:
            result = await provider_search.search_bangumi(
                query, run_id=prepared.run_id, limit=SEARCH_LIMIT, before_write=guard
            )
            if not result.available:
                raise RuntimeError("Bangumi search provider is unavailable.")
            for item in result.results:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    candidates.append({**item, "matched_query": query})
        candidates = candidates[:16]
        if not candidates:
            return await finish(
                prepared,
                "no_match",
                {
                    "subject_id": None,
                    "queries": queries,
                    "candidates": 0,
                    "reason": "Bangumi search returned no anime subjects.",
                },
            )
        decision = await select_subject(prepared, candidates)
        if decision.decision != "found" or decision.confidence < MIN_CONFIDENCE:
            return await finish(
                prepared,
                "abstained",
                {
                    "subject_id": None,
                    "queries": queries,
                    "candidates": len(candidates),
                    "reason": "Model abstained or confidence was below threshold.",
                },
            )
        assert decision.subject_id is not None
        async with session_scope() as session:
            await own(session, prepared)
            await artifacts.capture(
                session,
                payload={
                    "root_entity_id": str(prepared.root_id),
                    "subject_id": decision.subject_id,
                    "confidence": str(decision.confidence),
                    "reason": decision.reason,
                },
                kind="internal_snapshot",
                source_url=f"https://bgm.tv/subject/{decision.subject_id}",
                tool_name="bangumi.link",
                tool_version=PROMPT_VERSION,
                metadata={"selected": True},
            )
        entity_id, episodes = await sync_subject(prepared, decision.subject_id)
        binding_error = ""
        async with session_scope() as session:
            await own(session, prepared)
            source = await resolution.resolve(session, prepared.root_id)
            target = await resolution.resolve(session, entity_id)
            candidate = (
                await create_candidate(session, prepared, target, decision)
                if source != target
                else None
            )
            if apply and candidate:
                try:
                    async with session.begin_nested():
                        await resolution.decide(
                            session,
                            candidate_id=candidate,
                            outcome="bind",
                            decided_by="ai_bangumi_search",
                            reason=(
                                f"AI Bangumi search matched subject {decision.subject_id} at "
                                f"{decision.confidence} confidence; evidence includes MAL title "
                                "and Bangumi search result."
                            ),
                        )
                except resolution.ResolutionError as error:
                    await resolution.decide(
                        session,
                        candidate_id=candidate,
                        outcome="abstain",
                        decided_by="ai_bangumi_search",
                        reason=f"Bangumi link could not be bound safely: {error}",
                    )
                    binding_error = str(error)
        if source == target:
            return await finish(
                prepared,
                "already_linked",
                {"subject_id": decision.subject_id, "canonical_entity_id": str(source)},
            )
        if candidate is None:
            return await finish(
                prepared,
                "abstained",
                {
                    "subject_id": decision.subject_id,
                    "reason": "Canonical pair is not a compatible anime Work.",
                },
            )
        if binding_error:
            return await finish(
                prepared,
                "abstained",
                {
                    "subject_id": decision.subject_id,
                    "candidate_id": str(candidate),
                    "error": binding_error,
                },
            )
        details = {
            "subject_id": decision.subject_id,
            "candidate_id": str(candidate),
            "confidence": str(decision.confidence),
            "episodes_synced": episodes,
            "reason": decision.reason,
        }
        await finish(prepared, "linked" if apply else "candidate_pending", details)
        if not apply:
            return {
                "root_entity_id": str(prepared.root_id),
                "outcome": "candidate_pending",
                "subject_id": decision.subject_id,
                "candidate_id": str(candidate),
            }
        return {
            "root_entity_id": str(prepared.root_id),
            "outcome": "linked",
            "attempt_id": str(prepared.run_id),
            **details,
        }
    except Exception as error:
        return await failed(prepared, error)


async def run_missing(
    *, limit: int | None = None, force: bool = False, apply: bool = False
) -> dict[str, Any]:
    maximum = max(
        1, int(limit if limit is not None else os.environ.get("BANGUMI_LINK_BATCH_SIZE", "50"))
    )
    walk_cap = max(1, int(os.environ.get("BANGUMI_LINK_WALK_CAP", "40000")))
    async with session_scope() as session:
        rows = await fetch(
            session,
            "SELECT DISTINCT rep.entity_id FROM entity_representation rep "
            "JOIN provider_record r ON r.id=rep.provider_record_id "
            "JOIN provider_namespace ns ON ns.id=r.namespace_id "
            "JOIN provider p ON p.id=ns.provider_id JOIN entity e ON e.id=rep.entity_id "
            "WHERE rep.is_active AND r.status='active' AND p.slug='mal' AND ns.slug='anime' "
            "AND e.lifecycle='active' ORDER BY rep.entity_id LIMIT :limit",
            {"limit": walk_cap},
        )
    summaries: list[dict[str, Any]] = []
    processed = set()
    walked = 0
    for row in rows:
        if len(summaries) >= maximum:
            break
        walked += 1
        async with session_scope() as session:
            root = await resolution.resolve(session, row.entity_id)
            if root in processed:
                continue
            processed.add(root)
            if not await needs_link(session, root):
                continue
        try:
            result = await attempt(root, apply=apply, force=force)
        except Exception as error:
            result = {
                "root_entity_id": str(root),
                "outcome": "failed",
                "error": f"{type(error).__name__}: {error}"[:2000],
            }
        if result.get("outcome") not in {"skipped_existing", "already_running"}:
            summaries.append(result)
    return {
        "policy_version": POLICY_VERSION,
        "processed": len(summaries),
        "scanned": walked,
        "results": summaries,
    }
