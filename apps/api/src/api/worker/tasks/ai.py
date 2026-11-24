"""Model matching tasks with bounded dispatch and classified provider retries."""

from __future__ import annotations

import os
from typing import Any, NoReturn

from celery import shared_task
from celery.exceptions import Ignore

from api.config import settings
from api.contexts.knowledge.service import classify_entity
from api.contexts.matching.service import evaluate
from api.db import fetch
from api.shared.ai import AIError
from api.shared.ai_availability import provider_available
from api.shared.dispatch import publish
from api.worker.runtime import run
from api.worker.session import session_scope

EVALUATE_TASK = "apps.ai.tasks.evaluate_match_candidate_task"


async def dispatch_pending(limit: int | None = None) -> dict[str, Any]:
    if not settings.ai_base_url or not settings.ai_api_key or not await provider_available():
        return {"dispatched": 0, "reason": "ai_provider_unavailable"}
    batch = max(1, int(limit or os.environ.get("AI_MATCH_EVAL_BATCH_SIZE", "300")))
    async with session_scope() as session:
        rows = await fetch(
            session,
            """
            SELECT c.id FROM match_candidate c WHERE c.status = 'pending'
              AND NOT EXISTS (SELECT 1 FROM ai_proposal p WHERE p.match_candidate_id = c.id)
            ORDER BY c.created_at, c.id LIMIT :limit
        """,
            {"limit": batch},
        )
        candidate_ids = [str(row.id) for row in rows]
    sent = [
        value
        for value in candidate_ids
        if publish(EVALUATE_TASK, {"candidate_id": value}, queue="ai")
    ]
    return {"dispatched": len(sent), "candidate_ids": sent}


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.ai.tasks.evaluate_match_candidate_task",
    queue="ai",
    bind=True,
    max_retries=3,
    soft_time_limit=180,
    time_limit=210,
)
def evaluate_match_candidate_task(self: Any, candidate_id: str) -> str:
    try:
        result: str = run(evaluate(candidate_id))
        return result
    except AIError as error:
        retry_provider(self, error)


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.ai.tasks.evaluate_pending_candidates_task",
    queue="ai",
    soft_time_limit=900,
    time_limit=960,
)
def evaluate_pending_candidates_task(limit: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = run(dispatch_pending(limit))
    return result


def retry_provider(task: Any, error: AIError, *, max_retries: int = 3) -> NoReturn:
    if not error.retryable:
        raise Ignore() from error
    raise task.retry(
        exc=error, countdown=min(300, 30 * 2**task.request.retries), max_retries=max_retries
    ) from error


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.ai.tasks.classify_entity_task",
    queue="ai",
    bind=True,
    max_retries=3,
    soft_time_limit=180,
    time_limit=210,
)
def classify_entity_task(self: Any, entity_id: str) -> str:
    try:
        result: str = run(classify_entity(entity_id))
        return result
    except AIError as error:
        retry_provider(self, error)
