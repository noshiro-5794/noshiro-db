"""Audited, read-only provider search used by identity-retrieval workflows."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.knowledge import agent_runs, artifacts
from api.contexts.knowledge.agent_runs import WriteGuard
from api.contexts.presentation.fragments import fetch
from api.worker.providers.bangumi import BangumiClient
from api.worker.providers.errors import ProviderError
from api.worker.session import session_scope


class SearchResult(BaseModel):
    available: bool
    reason: str = ""
    total: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)


async def authorize(session: AsyncSession, run_id: UUID, permission: str) -> None:
    rows = await fetch(
        session, "SELECT status,metadata FROM agent_run WHERE id=:id FOR UPDATE", {"id": run_id}
    )
    if not rows or rows[0].status != "running":
        raise RuntimeError("The agent run is not running.")
    if permission not in (rows[0].metadata or {}).get("scopes", []):
        raise PermissionError(f"Missing required scope '{permission}'.")


async def invoke(
    *,
    run_id: UUID,
    tool: str,
    permission: str,
    parameters: dict[str, Any],
    handler: Callable[[], Awaitable[SearchResult]],
    before_write: WriteGuard | None = None,
) -> SearchResult:
    async with session_scope() as session:
        await authorize(session, run_id, permission)
        if before_write is not None:
            await before_write(session)
        step = await agent_runs.create_step(
            session, run_id=run_id, skill="", payload=parameters, kind="tool"
        )
        invocation = (
            await fetch(
                session,
                "INSERT INTO tool_invocation "
                "(id,step_id,tool_name,tool_version,status,parameters,parameter_hash,error,"
                "idempotency_key,idempotency_scope,permission_scope,risk_level,has_side_effects,"
                "created_at,started_at) "
                "SELECT gen_random_uuid(),:step,:tool,'1.0.0','running',CAST(:parameters AS jsonb),"
                ":hash,'',:key,COALESCE(NULLIF(idempotency_scope,''),'system'),:permission,"
                "'read_only',false,now(),now() FROM agent_run WHERE id=:run RETURNING id",
                {
                    "step": step,
                    "tool": tool,
                    "parameters": json.dumps(parameters),
                    "hash": agent_runs.payload_hash(parameters),
                    "key": f"{tool}:{step}",
                    "permission": permission,
                    "run": run_id,
                },
            )
        )[0].id
    try:
        result = await handler()
        failure_reason = (
            (result.reason or "Provider search is unavailable.") if not result.available else ""
        )
        async with session_scope() as session:
            await authorize(session, run_id, permission)
            if before_write is not None:
                await before_write(session)
            for item in result.results:
                await artifacts.capture(
                    session,
                    payload=item,
                    kind="search_result",
                    source_url=str(item.get("url") or ""),
                    tool_name=tool,
                    tool_version="1.0.0",
                    invocation_id=invocation,
                    metadata={"query": parameters.get("keyword") or parameters.get("query") or ""},
                )
            await fetch(
                session,
                "UPDATE tool_invocation SET status=:status,result=CAST(:output AS jsonb),"
                "error=:error,"
                "finished_at=clock_timestamp() WHERE id=:id RETURNING id",
                {
                    "id": invocation,
                    "status": "succeeded" if result.available else "failed",
                    "output": result.model_dump_json(),
                    "error": failure_reason[:4000],
                },
            )
            await agent_runs.finish_step(
                session,
                step,
                result.model_dump(),
                error=failure_reason,
            )
        return result
    except Exception as error:
        reason = f"{type(error).__name__}: {error}"[:4000]
        async with session_scope() as session:
            await fetch(
                session,
                "UPDATE tool_invocation SET status='failed',error=:error,"
                "finished_at=clock_timestamp() "
                "WHERE id=:id RETURNING id",
                {"id": invocation, "error": reason},
            )
            await agent_runs.finish_step(session, step, None, error=reason)
        raise


def bangumi_result(payload: dict[str, Any]) -> SearchResult:
    results = []
    for item in payload.get("data") or []:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            continue
        images = item.get("images")
        images = images if isinstance(images, dict) else {}
        identifier = int(item["id"])
        results.append(
            {
                "id": identifier,
                "name": str(item.get("name") or ""),
                "name_cn": str(item.get("name_cn") or ""),
                "date": item.get("date"),
                "summary": str(item.get("summary") or "")[:800],
                "platform": str(item.get("platform") or ""),
                "images": {key: str(value) for key, value in images.items() if value},
                "url": f"https://bgm.tv/subject/{identifier}",
            }
        )
    total = payload.get("total")
    return SearchResult(
        available=True,
        total=int(total) if isinstance(total, int) else len(results),
        results=results,
    )


async def search_bangumi(
    keyword: str, *, run_id: UUID, limit: int = 8, before_write: WriteGuard | None = None
) -> SearchResult:
    async def search() -> SearchResult:
        async with session_scope() as session:
            rows = await fetch(
                session, "SELECT storage_policy FROM provider WHERE slug='bangumi'", {}
            )
        client = BangumiClient()
        client.forbid_storage(forbidden=bool(rows and rows[0].storage_policy == "forbidden"))
        try:
            payload = await asyncio.to_thread(
                client.search_subjects, keyword=keyword, subject_types=(2,), limit=limit, offset=0
            )
            return bangumi_result(payload)
        except ProviderError as error:
            return SearchResult(available=False, reason=f"{type(error).__name__}: {error}"[:1000])
        finally:
            client.close()

    return await invoke(
        run_id=run_id,
        tool="bangumi.search_subjects",
        permission="bangumi:search",
        parameters={"keyword": keyword, "limit": limit, "offset": 0},
        handler=search,
        before_write=before_write,
    )
