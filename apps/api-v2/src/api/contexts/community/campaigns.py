"""A sync campaign with the throughput it is currently achieving."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat

QUERY = """
    SELECT campaign.id, campaign.provider_slug, campaign.campaign_type,
           campaign.status, campaign.ai_mode, campaign.parameters,
           campaign.total_items, campaign.processed_items, campaign.synced_items,
           campaign.skipped_items, campaign.failed_items,
           campaign.quality_report, campaign.cost, campaign.error,
           campaign.heartbeat_at, campaign.next_run_at, campaign.created_at,
           campaign.started_at, campaign.finished_at, campaign.updated_at,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'queued')
             AS queued,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'running')
             AS running,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'succeeded')
             AS succeeded,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'failed')
             AS failed,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.next_retry_at IS NOT NULL)
             AS retry_waiting,
           EXTRACT(EPOCH FROM (now() - campaign.started_at)) AS elapsed_seconds
    FROM sync_campaign AS campaign WHERE campaign.id = CAST(:id AS uuid)
"""


async def campaign(session: AsyncSession, *, campaign_id: str) -> dict[str, Any]:
    rows = await fetch(session, QUERY, {"id": campaign_id})
    if not rows:
        raise LookupError(campaign_id)
    row = rows[0]
    elapsed = float(row.elapsed_seconds or 0)
    throughput = row.processed_items / elapsed if elapsed > 0 else None
    remaining = max(0, row.total_items - row.processed_items)
    percent = round(row.processed_items / row.total_items * 100, 2) if row.total_items else None
    return {
        "id": str(row.id),
        "provider_slug": row.provider_slug,
        "campaign_type": row.campaign_type,
        "status": row.status,
        "ai_mode": row.ai_mode,
        "parameters": row.parameters if isinstance(row.parameters, dict) else {},
        "total_items": row.total_items,
        "processed_items": row.processed_items,
        "synced_items": row.synced_items,
        "skipped_items": row.skipped_items,
        "failed_items": row.failed_items,
        "quality_report": row.quality_report,
        "cost": float(row.cost) if row.cost is not None else None,
        "error": row.error,
        "heartbeat_at": isoformat(row.heartbeat_at),
        "next_run_at": isoformat(row.next_run_at),
        "created_at": isoformat(row.created_at),
        "started_at": isoformat(row.started_at),
        "finished_at": isoformat(row.finished_at),
        "updated_at": isoformat(row.updated_at),
        "progress": {
            "percent": percent,
            "queued": int(row.queued),
            "running": int(row.running),
            "succeeded": int(row.succeeded),
            "failed": int(row.failed),
            "retry_waiting": int(row.retry_waiting),
            "throughput_items_per_second": round(throughput, 4) if throughput is not None else None,
            "eta_seconds": round(remaining / throughput)
            if throughput is not None and throughput > 0
            else None,
        },
    }


async def campaign_items(
    session: AsyncSession,
    *,
    campaign_id: str,
    status: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    await campaign(session, campaign_id=campaign_id)
    where = "item.campaign_id = CAST(:campaign AS uuid)"
    params: dict[str, Any] = {"campaign": campaign_id}
    if status:
        where += " AND item.status = :status"
        params["status"] = status
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM sync_work_item AS item WHERE {where}",
        params,
    )
    rows = await fetch(
        session,
        "SELECT item.id, item.shard, item.cursor, item.status, item.provider_record,"
        " item.result, item.error, item.attempt, item.next_retry_at,"
        " item.last_error_code, item.ai_processed_at, item.ai_enriched_at,"
        " item.started_at, item.finished_at, item.updated_at"
        f" FROM sync_work_item AS item WHERE {where}"
        " ORDER BY item.shard, item.id LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "shard": row.shard,
            "cursor": row.cursor,
            "status": row.status,
            "provider_record": row.provider_record,
            "result": row.result,
            "error": row.error,
            "attempt": row.attempt,
            "next_retry_at": isoformat(row.next_retry_at),
            "last_error_code": row.last_error_code,
            "ai_processed_at": isoformat(row.ai_processed_at),
            "ai_enriched_at": isoformat(row.ai_enriched_at),
            "started_at": isoformat(row.started_at),
            "finished_at": isoformat(row.finished_at),
            "updated_at": isoformat(row.updated_at),
        }
        for row in rows
    ]
