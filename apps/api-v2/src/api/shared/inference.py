"""Persistent inference audit shared by model-driven workflows."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

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
    *, payload: dict[str, Any], use_case: str, prompt_version: str, metadata: dict[str, Any]
) -> UUID:
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            INSERT INTO ai_run (id, use_case, provider, model, prompt_version, input_hash,
              input_metadata, status, error, created_at, started_at)
            VALUES (gen_random_uuid(), :use_case, 'openai_compatible', :model, :prompt,
              :hash, CAST(:metadata AS jsonb), 'running', '', now(), now()) RETURNING id
        """,
            {
                "use_case": use_case,
                "model": settings.ai_model,
                "prompt": prompt_version,
                "hash": digest,
                "metadata": json.dumps(metadata),
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
