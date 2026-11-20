"""Leased, bounded campaign steps with durable source/AI checkpoints and rescheduling."""

import json
import logging
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import UUID

from celery import current_task, shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.synchronization import campaign_ai, campaigns, discovery_step, work_items
from api.contexts.synchronization.discovery_step import positive_int
from api.contexts.synchronization.domain import PHASES, PROVIDER_NAMESPACES, TERMINAL, LeaseLost
from api.db import fetch
from api.worker import campaign_imports
from api.worker.runtime import run
from api.worker.session import session_scope

logger = logging.getLogger(__name__)
NEXT_PHASE = dict(zip(PHASES, (*PHASES[1:], "completed"), strict=True))


@dataclass(frozen=True, slots=True)
class StepResult:
    result: dict[str, Any]
    countdown: int | None


def snapshot(campaign: Any) -> dict[str, Any]:
    return {
        "campaign_id": str(campaign.id),
        "provider": campaign.provider_slug,
        "status": campaign.status,
        "processed_items": campaign.processed_items,
        "failed_items": campaign.failed_items,
    }


async def renew(session: AsyncSession, campaign_id: UUID, owner: str) -> None:
    if not await campaigns.heartbeat(session, campaign_id, owner, lease_seconds=1200):
        raise LeaseLost("Campaign lease expired before renewal.")


async def fetch_step(campaign_id: UUID, owner: str, maximum: int | None, deadline: float) -> bool:
    async with session_scope() as session:
        campaign = await campaigns.owned(session, campaign_id, owner, phase="fetching")
        params = campaign.parameters or {}
        limit = (
            max(0, int(maximum))
            if maximum is not None
            else positive_int(params.get("fetch_batch_size"), 50)
        )
    for _ in range(limit):
        if monotonic() >= deadline:
            return False
        async with session_scope() as session:
            campaign = await campaigns.owned(session, campaign_id, owner, phase="fetching")
            await renew(session, campaign_id, owner)
            items = await work_items.claim_items(
                session, campaign_id, owner, limit=1, lease_seconds=1200
            )
            if not items:
                break
            item = items[0]
            policy = await fetch(
                session,
                "SELECT storage_policy FROM provider WHERE slug=:provider",
                {"provider": campaign.provider_slug},
            )

        async def progress(label: str, total: int | None, *, item_id: UUID = item.id) -> None:
            async with session_scope() as session:
                await campaigns.owned(
                    session, campaign_id, owner, phase="fetching", allow_paused=True
                )
                await renew(session, campaign_id, owner)
                await work_items.heartbeat(session, item_id, owner)

        try:
            payload = await campaign_imports.fetch_source(
                campaign.provider_slug,
                item.cursor,
                forbidden=bool(policy and policy[0].storage_policy == "forbidden"),
                progress=progress,
            )
            async with session_scope() as session:
                await campaigns.owned(
                    session, campaign_id, owner, phase="fetching", allow_paused=True
                )
                await renew(session, campaign_id, owner)
                await work_items.owned_item(session, item.id, owner)
                entity_id = await campaign_imports.project_source(
                    session, campaign.provider_slug, item.cursor, payload
                )
                await work_items.succeed(
                    session,
                    item.id,
                    owner,
                    {"entity_id": str(entity_id), "external_id": item.cursor},
                )
        except LeaseLost:
            raise
        except Exception as error:
            async with session_scope() as session:
                await campaigns.owned(
                    session, campaign_id, owner, phase="fetching", allow_paused=True
                )
                await work_items.fail(
                    session,
                    item.id,
                    owner,
                    error,
                    max_attempts=positive_int(params.get("max_attempts"), 5),
                )
    async with session_scope() as session:
        campaign = await campaigns.owned(session, campaign_id, owner, phase="fetching")
        rows = await fetch(
            session,
            "SELECT status,count(*) AS n FROM sync_work_item WHERE campaign_id=:id GROUP BY status",
            {"id": campaign_id},
        )
        counts = {row.status: row.n for row in rows}
        if counts.get("queued", 0) or counts.get("running", 0):
            return False
        if counts.get("failed", 0):
            raise RuntimeError(f"{counts['failed']} provider work items exhausted retries.")
        return True


async def reconcile(session: AsyncSession, campaign: Any) -> None:
    params = campaign.parameters or {}
    discovery = params.get("discovery") or {}
    if (
        campaign.campaign_type != "full"
        or discovery.get("next_cursor")
        or discovery.get("truncated")
    ):
        return
    if not params.get("reconcile_missing", campaign.provider_slug in {"vndb", "anilist"}):
        return
    await fetch(
        session,
        """
        UPDATE provider_record r SET status='missing',updated_at=now()
        FROM provider_namespace ns,provider p WHERE r.namespace_id=ns.id AND ns.provider_id=p.id
          AND p.slug=:provider AND ns.slug=:namespace AND r.status='active'
          AND r.last_seen_at<=:started
          AND NOT EXISTS (SELECT 1 FROM sync_work_item i WHERE i.campaign_id=:campaign
                          AND i.cursor=r.external_id) RETURNING r.id
    """,
        {
            "provider": campaign.provider_slug,
            "namespace": PROVIDER_NAMESPACES[campaign.provider_slug],
            "campaign": campaign.id,
            "started": campaign.started_at,
        },
    )


async def review(session: AsyncSession, campaign: Any) -> None:
    await campaigns.refresh_counts(session, campaign.id)
    campaign = await campaigns.get_campaign(session, campaign.id)
    params = dict(campaign.parameters or {})
    pending = (
        await fetch(
            session,
            "SELECT count(*) AS n FROM ai_claim c JOIN agent_step s "
            "ON s.id=c.step_id WHERE s.run_id=:id AND c.status='proposed'",
            {"id": campaign.agent_run_id},
        )
    )[0].n
    report = {
        "total_items": campaign.total_items,
        "succeeded_items": campaign.synced_items,
        "failed_items": campaign.failed_items,
        "skipped_items": campaign.skipped_items,
        "ai_mode": campaign.ai_mode,
        "evidence_first": True,
        "ai_enrichment": params.get("enrichment")
        or {"claims": 0, "applied": 0, "abstained": 0, "skipped": 0},
        "ai_claims_pending_review": pending,
        "discovery_truncated": bool((params.get("discovery") or {}).get("truncated")),
    }
    if campaign.campaign_type == "incremental" and not report["discovery_truncated"]:
        watermark = params.pop("pending_watermark", None)
        if watermark is not None:
            params["watermark"] = watermark
    await fetch(
        session,
        "UPDATE sync_campaign SET quality_report=CAST(:report AS jsonb),"
        "parameters=CAST(:params AS jsonb),next_run_at=NULL,updated_at=now() "
        "WHERE id=:id RETURNING id",
        {"id": campaign.id, "report": json.dumps(report), "params": json.dumps(params)},
    )
    if campaign.agent_run_id is not None:
        await fetch(
            session,
            "UPDATE agent_run SET status='succeeded',finished_at=now(),updated_at=now() "
            "WHERE id=:id AND status=ANY(:statuses) RETURNING id",
            {"id": campaign.agent_run_id, "statuses": ["queued", "running"]},
        )


async def process(campaign_id: UUID, owner: str, maximum: int | None, deadline: float) -> None:
    while monotonic() < deadline:
        async with session_scope() as session:
            campaign = await campaigns.get_campaign(session, campaign_id)
            phase = campaign.status
            if phase not in PHASES:
                return
            await campaigns.owned(session, campaign_id, owner, phase=phase)
            await renew(session, campaign_id, owner)
        if phase == "discovering":
            async with session_scope() as session:
                complete = await discovery_step.discover_step(session, campaign_id, owner)
        elif phase == "fetching":
            complete = await fetch_step(campaign_id, owner, maximum, deadline)
        elif phase in {"normalizing", "enriching"}:
            complete = await campaign_ai.run_phase(campaign_id, owner, phase, deadline=deadline)
        else:
            async with session_scope() as session:
                campaign = await campaigns.owned(session, campaign_id, owner, phase=phase)
                if phase == "reconciling":
                    await reconcile(session, campaign)
                elif phase == "reviewing":
                    await review(session, campaign)
                if not await campaigns.transition(session, campaign_id, phase, NEXT_PHASE[phase]):
                    raise LeaseLost("Campaign phase changed before its transition.")
            continue
        if not complete:
            return
        async with session_scope() as session:
            await campaigns.owned(session, campaign_id, owner, phase=phase)
            if phase == "discovering":
                await campaigns.refresh_counts(session, campaign_id)
            if not await campaigns.transition(session, campaign_id, phase, NEXT_PHASE[phase]):
                raise LeaseLost("Campaign phase changed before its transition.")


async def next_delay(session: AsyncSession, campaign: Any) -> int:
    base = positive_int((campaign.parameters or {}).get("step_delay_seconds"), 1)
    if campaign.status != "fetching":
        return base
    ready = await fetch(
        session,
        "SELECT 1 FROM sync_work_item WHERE campaign_id=:id "
        "AND ((status='queued' AND "
        "(next_retry_at IS NULL OR next_retry_at<=clock_timestamp())) "
        "OR (status='running' AND lease_expires_at<clock_timestamp())) LIMIT 1",
        {"id": campaign.id},
    )
    if ready:
        return base
    row = (
        await fetch(
            session,
            """
        SELECT CEIL(EXTRACT(EPOCH FROM (MIN(ready_at)-clock_timestamp())))::integer AS delay FROM (
          SELECT next_retry_at AS ready_at FROM sync_work_item
            WHERE campaign_id=:id AND status='queued' AND next_retry_at>clock_timestamp()
          UNION ALL SELECT lease_expires_at FROM sync_work_item
            WHERE campaign_id=:id AND status='running' AND lease_expires_at>clock_timestamp()
        ) waits
    """,
            {"id": campaign.id},
        )
    )[0]
    return max(base, row.delay or 0)


async def lease_delay(session: AsyncSession, campaign_id: UUID) -> int:
    rows = await fetch(
        session,
        "SELECT GREATEST(1,CEIL(EXTRACT(EPOCH FROM (lease_expires_at-clock_timestamp()))))"
        "::integer AS delay FROM sync_campaign WHERE id=:id",
        {"id": campaign_id},
    )
    return rows[0].delay or 1


async def execute(campaign_id: str, *, max_items: int | None, owner: str) -> StepResult:
    identifier = UUID(campaign_id)
    async with session_scope() as session:
        campaign = await campaigns.get_campaign(session, identifier)
        if campaign.status in TERMINAL:
            return StepResult(snapshot(campaign), None)
        claimed = await campaigns.claim_campaign(session, identifier, owner, lease_seconds=1200)
        if claimed is None:
            campaign = await campaigns.get_campaign(session, identifier)
            delay = (
                None
                if campaign.status in TERMINAL or campaign.status == "failed"
                else await lease_delay(session, identifier)
            )
            return StepResult(snapshot(campaign), delay)
        if claimed.status == "failed":
            claimed = await campaigns.resume_failed(session, identifier)
        if claimed.status == "queued":
            await campaigns.transition(session, identifier, "queued", "discovering")
        budget = min(positive_int((claimed.parameters or {}).get("step_budget_seconds"), 240), 3300)
    try:
        await process(identifier, owner, max_items, monotonic() + budget)
    except LeaseLost:
        pass
    except Exception as error:
        logger.exception("Campaign step failed", extra={"campaign_id": campaign_id})
        async with session_scope() as session:
            await fetch(
                session,
                "UPDATE sync_campaign SET status='failed',error=:error,"
                "finished_at=now(),next_run_at=NULL,updated_at=now() WHERE id=:id "
                "AND lease_owner=:owner AND lease_expires_at>clock_timestamp() "
                "AND status=ANY(:phases) RETURNING id",
                {
                    "id": identifier,
                    "owner": owner,
                    "phases": list(PHASES),
                    "error": f"{type(error).__name__}: {error}"[:4000],
                },
            )
    finally:
        async with session_scope() as session:
            released = await campaigns.release(session, identifier, owner)
            campaign = await campaigns.get_campaign(session, identifier, lock=True)
            countdown = None
            if campaign.status not in TERMINAL and campaign.status != "failed":
                if not released and campaign.lease_owner:
                    countdown = await lease_delay(session, identifier)
                else:
                    countdown = await next_delay(session, campaign)
                    await fetch(
                        session,
                        "UPDATE sync_campaign SET next_run_at=clock_timestamp()+"
                        "make_interval(secs=>:delay),updated_at=now() WHERE id=:id RETURNING id",
                        {"id": identifier, "delay": countdown},
                    )
    return StepResult(snapshot(campaign), countdown)


class CampaignPublishError(RuntimeError):
    """A durable continuation could not be handed to the broker."""


async def record_publish_failure(campaign_id: str, error: Exception) -> None:
    async with session_scope() as session:
        await fetch(
            session,
            "UPDATE sync_campaign SET status='failed',error=:error,finished_at=now(),"
            "next_run_at=NULL,updated_at=now() WHERE id=:id AND lease_owner='' "
            "AND status=ANY(:phases) RETURNING id",
            {
                "id": UUID(campaign_id),
                "phases": list(PHASES),
                "error": f"{type(error).__name__}: Could not schedule next campaign step.",
            },
        )


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.sync.tasks.campaign.run_sync_campaign_task",
    queue="sync",
    soft_time_limit=3600,
    time_limit=3900,
    reject_on_worker_lost=True,
    autoretry_for=(CampaignPublishError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 3},
)
def run_sync_campaign_task(campaign_id: str, *, max_items: int | None = None) -> dict[str, Any]:
    outcome: StepResult = run(
        execute(campaign_id, max_items=max_items, owner=f"celery:{current_task.request.id}")
    )
    if outcome.countdown is not None:
        try:
            run_sync_campaign_task.apply_async(
                args=[campaign_id], kwargs={"max_items": max_items}, countdown=outcome.countdown
            )
        except Exception as error:
            run(record_publish_failure(campaign_id, error))
            raise CampaignPublishError("Campaign continuation dispatch failed.") from error
    return outcome.result
