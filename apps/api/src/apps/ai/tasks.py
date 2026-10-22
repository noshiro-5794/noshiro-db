import logging

from celery import shared_task
from celery.exceptions import Ignore
from django.conf import settings

from apps.ai.services import (
    ai_knowledge_proposal_service,
    ai_matching_batch_service,
    ai_matching_service,
    schedule_completion_service,
)
from integrations.ai import AIProviderError

logger = logging.getLogger(__name__)


def _retry_provider_call(
    task,
    error: AIProviderError,
    *,
    max_retries: int,
) -> None:
    """Retry a provider call only when another attempt could plausibly succeed.

    ``AIProviderError.retryable`` is false for account problems (401/402/403)
    and for a provider the gateway has already marked unavailable. Celery's
    ``autoretry_for`` cannot express that distinction — it retries every
    instance of the exception — so the tasks make the decision here. Without
    it, an unpaid balance turns one dispatched batch into thousands of retries:
    measured once at 18,412 failed runs in ten minutes.
    """
    if not error.retryable:
        logger.warning(
            "AI provider error is terminal; not retrying: %s", str(error)[:200]
        )
        raise Ignore() from error
    task.retry(
        exc=error,
        countdown=min(300, 30 * 2**task.request.retries),
        max_retries=max_retries,
    )


@shared_task(bind=True, max_retries=3, soft_time_limit=180, time_limit=210)
def evaluate_match_candidate_task(self, candidate_id: str) -> str:
    try:
        return str(ai_matching_service.evaluate(candidate_id=candidate_id).id)
    except AIProviderError as error:
        _retry_provider_call(self, error, max_retries=3)
        raise


@shared_task(bind=True, max_retries=3, soft_time_limit=180, time_limit=210)
def classify_entity_task(self, entity_id: str) -> str:
    try:
        return str(
            ai_knowledge_proposal_service.classify_entity(entity_id=entity_id).id
        )
    except AIProviderError as error:
        _retry_provider_call(self, error, max_retries=3)
        raise


@shared_task(bind=True, max_retries=3, soft_time_limit=180, time_limit=210)
def extract_observation_evidence_task(self, observation_id: str, entity_id: str) -> str:
    try:
        proposal = ai_knowledge_proposal_service.extract_evidence(
            observation_id=observation_id,
            entity_id=entity_id,
        )
    except AIProviderError as error:
        _retry_provider_call(self, error, max_retries=3)
        raise
    return str(proposal.id)


@shared_task(bind=True, max_retries=2, soft_time_limit=600, time_limit=700)
def complete_missing_schedule_slots_task(
    self,
    *,
    limit: int | None = None,
    apply: bool = True,
) -> dict:
    try:
        return schedule_completion_service.run(limit=limit, apply=apply)
    except AIProviderError as error:
        _retry_provider_call(self, error, max_retries=2)
        raise


@shared_task(
    soft_time_limit=900,
    time_limit=960,
)
def evaluate_pending_candidates_task(limit: int | None = None) -> dict:
    batch_size = max(1, int(limit or settings.AI_MATCH_EVAL_BATCH_SIZE))
    return ai_matching_batch_service.dispatch(limit=batch_size)
