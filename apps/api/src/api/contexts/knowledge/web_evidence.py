"""Cached, durable search artifacts used by multilingual enrichment."""

import json
import os
from typing import Any
from uuid import UUID

from api.contexts.knowledge import agent_runs
from api.contexts.knowledge import artifacts as evidence_artifacts
from api.db import fetch
from api.shared.web_search import configured, search
from api.worker.session import session_scope

SearchArtifact = evidence_artifacts.Artifact


async def cached(parameters: dict[str, Any]) -> list[SearchArtifact]:
    days = max(0, int(os.environ.get("WEB_SEARCH_CACHE_DAYS", "30")))
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            WITH recent AS (
              SELECT id FROM tool_invocation WHERE tool_name='web.search'
                AND tool_version='1.0.0' AND parameter_hash=:hash AND status='succeeded'
                AND finished_at>=clock_timestamp()-make_interval(days=>:days)
              ORDER BY finished_at DESC LIMIT 1
            )
            SELECT a.id,a.source_url,a.content_hash,a.excerpt,a.metadata FROM source_artifact a
            JOIN recent r ON r.id=a.tool_invocation_id ORDER BY a.created_at,a.id
            """,
            {"hash": agent_runs.payload_hash(parameters), "days": days},
        )
        return [SearchArtifact(**row._mapping) for row in rows]


async def gather(query: str, *, entity_id: UUID, run_id: UUID) -> list[SearchArtifact]:
    if not query.strip():
        return []
    parameters = {"query": query, "max_results": 5}
    artifacts = await cached(parameters)
    if artifacts:
        return artifacts
    async with session_scope() as session:
        step_id = await agent_runs.create_step(
            session, run_id=run_id, skill="", payload=parameters, kind="tool"
        )
        rows = await fetch(
            session,
            """
            INSERT INTO tool_invocation
              (id,step_id,tool_name,tool_version,status,parameters,parameter_hash,error,
               idempotency_key,idempotency_scope,permission_scope,risk_level,has_side_effects,
               created_at,started_at)
            SELECT gen_random_uuid(),:step,'web.search','1.0.0','running',
              CAST(:parameters AS jsonb),:hash,'',:key,
              COALESCE(NULLIF(idempotency_scope,''),'system'),
              'knowledge:read','read_only',false,now(),now() FROM agent_run WHERE id=:run
            RETURNING id
            """,
            {
                "step": step_id,
                "run": run_id,
                "parameters": json.dumps(parameters),
                "hash": agent_runs.payload_hash(parameters),
                "key": f"enrich:{entity_id}:web.search:{step_id}",
            },
        )
        invocation_id = rows[0].id
    try:
        results = await search(query, max_results=5)
        output = {"available": configured(), "results": results}
        async with session_scope() as session:
            await fetch(
                session,
                "UPDATE tool_invocation SET status='succeeded',result=CAST(:output AS jsonb),"
                "finished_at=clock_timestamp() WHERE id=:id RETURNING id",
                {"id": invocation_id, "output": json.dumps(output)},
            )
            await agent_runs.finish_step(session, step_id, output)
            artifacts = []
            for item in results:
                if not item.get("url"):
                    continue
                artifacts.append(
                    await evidence_artifacts.capture(
                        session,
                        payload=item,
                        kind="search_result",
                        source_url=str(item["url"]),
                        tool_name="web.search",
                        tool_version="1.0.0",
                        invocation_id=invocation_id,
                        metadata={
                            "title": str(item.get("title", "")),
                            "score": item.get("score"),
                        },
                    )
                )
            return artifacts
    except Exception as error:
        reason = f"{type(error).__name__}: {error}"[:4000]
        async with session_scope() as session:
            await fetch(
                session,
                "UPDATE tool_invocation SET status='failed',error=:error,"
                "finished_at=clock_timestamp() WHERE id=:id RETURNING id",
                {"id": invocation_id, "error": reason},
            )
            await agent_runs.finish_step(session, step_id, None, error=reason)
        return []
