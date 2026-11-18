"""Persistent inference audit shared by model-driven workflows."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.contexts.presentation.fragments import fetch
from api.worker.session import session_scope


def optional_number(value: Any, *, integer: bool = False) -> Decimal | int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            return None
        return int(number) if integer else number
    except (ValueError, InvalidOperation, OverflowError):
        return None


async def start_run(
    *,
    payload: dict[str, Any],
    use_case: str,
    prompt_version: str,
    metadata: dict[str, Any],
    agent_step_id: UUID | None = None,
    model: str | None = None,
) -> UUID:
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            INSERT INTO ai_run (id, use_case, provider, model, prompt_version, input_hash,
              input_metadata, status, error, created_at, started_at, agent_step_id)
            VALUES (gen_random_uuid(), :use_case, 'openai_compatible', :model, :prompt,
              :hash, CAST(:metadata AS jsonb), 'running', '', now(), now(), :step) RETURNING id
        """,
            {
                "use_case": use_case,
                "model": model or settings.ai_model,
                "prompt": prompt_version,
                "hash": digest,
                "metadata": json.dumps(metadata),
                "step": agent_step_id,
            },
        )
        return UUID(str(rows[0].id))


async def fail_run(run_id: UUID, error: Exception) -> None:
    # Failure audit must survive rollback of candidate and proposal writes.
    async with session_scope() as session:
        await fetch(
            session,
            """
            UPDATE ai_run SET status = 'failed', error = :error, finished_at = now()
            WHERE id = :id RETURNING id
        """,
            {"id": run_id, "error": f"{type(error).__name__}: {error}"[:4000]},
        )


async def finish_run(
    run_id: UUID, output: dict[str, Any], usage: dict[str, Any], *, latency_ms: int | None = None
) -> None:
    async with session_scope() as session:
        await store_result(session, run_id, output, usage, latency_ms=latency_ms)


async def store_result(
    session: AsyncSession,
    run_id: UUID,
    output: dict[str, Any],
    usage: dict[str, Any],
    *,
    latency_ms: int | None = None,
    model: str | None = None,
) -> None:
    await fetch(
        session,
        """
        UPDATE ai_run SET status='succeeded',error='',output=CAST(:output AS jsonb),
          input_tokens=:input,output_tokens=:tokens,cost=:cost,latency_ms=:latency,model=COALESCE(:model,model),
          finished_at=now() WHERE id=:id RETURNING id
        """,
        {
            "id": run_id,
            "output": json.dumps(output),
            "input": optional_number(
                usage.get("input_tokens", usage.get("prompt_tokens")), integer=True
            ),
            "tokens": optional_number(
                usage.get("output_tokens", usage.get("completion_tokens")), integer=True
            ),
            "cost": optional_number(usage.get("cost")),
            "latency": latency_ms,
            "model": model,
        },
    )
