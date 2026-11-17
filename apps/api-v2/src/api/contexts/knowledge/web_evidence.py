"""Cached, durable search artifacts used by multilingual enrichment."""

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from api.contexts.knowledge import agent_runs
from api.contexts.presentation.fragments import fetch
from api.shared.web_search import configured, search
from api.worker.session import session_scope


@dataclass(frozen=True, slots=True)
class SearchArtifact:
    id: UUID
    source_url: str
    content_hash: str
    excerpt: str
    metadata: dict[str, Any]


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
                text = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                encoded = text.encode()
                rows = await fetch(
                    session,
                    """
                    INSERT INTO source_artifact
                      (id,tool_invocation_id,kind,source_url,content_hash,mime_type,byte_size,
                       excerpt,object_key,metadata,license_info,fetched_at,created_at)
                    VALUES (gen_random_uuid(),:invocation,'search_result',:url,:hash,
                      'application/json',:size,:excerpt,'',CAST(:metadata AS jsonb),'',
                      clock_timestamp(),clock_timestamp())
                    RETURNING id,source_url,content_hash,excerpt,metadata
                    """,
                    {
                        "invocation": invocation_id,
                        "url": str(item["url"]),
                        "hash": hashlib.sha256(encoded).hexdigest(),
                        "size": len(encoded),
                        "excerpt": text[:8000],
                        "metadata": json.dumps(
                            {
                                "title": str(item.get("title", "")),
                                "score": item.get("score"),
                                "tool_name": "web.search",
                                "tool_version": "1.0.0",
                            }
                        ),
                    },
                )
                artifacts.append(SearchArtifact(**rows[0]._mapping))
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
