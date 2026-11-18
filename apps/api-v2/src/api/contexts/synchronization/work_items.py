"""Idempotent discovery rows and ownership-checked work acknowledgements."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.campaigns import get_campaign
from api.contexts.synchronization.domain import LeaseLost, classify_failure


async def enqueue_page(
    session: AsyncSession, campaign_id: UUID, shard: int, external_ids: list[str]
) -> int:
    campaign = await get_campaign(session, campaign_id, lock=True)
    if campaign.status != "discovering":
        raise LeaseLost("Campaign is no longer discovering.")
    rows = await fetch(
        session,
        """
        INSERT INTO sync_work_item (id, campaign_id, shard, cursor, status, error, attempt,
          last_error_code, lease_owner, created_at, updated_at)
        SELECT gen_random_uuid(), :campaign, :shard, value, 'queued', '', 0, '', '', now(), now()
        FROM unnest(CAST(:ids AS text[])) AS value
        ON CONFLICT (campaign_id, shard, cursor) DO NOTHING RETURNING id
    """,
        {"campaign": campaign_id, "shard": shard, "ids": external_ids},
    )
    await fetch(
        session,
        "UPDATE sync_campaign SET total_items=total_items+:added,updated_at=now() "
        "WHERE id=:id RETURNING id",
        {"id": campaign_id, "added": len(rows)},
    )
    return len(rows)


async def claim_items(
    session: AsyncSession,
    campaign_id: UUID,
    owner: str,
    *,
    limit: int = 50,
    lease_seconds: int = 300,
) -> list[Any]:
    campaign = await get_campaign(session, campaign_id, lock=True)
    if campaign.status != "fetching":
        return []
    await fetch(
        session,
        """
        UPDATE sync_work_item SET status = 'queued', lease_owner = '', lease_expires_at = NULL,
          error = 'Worker lease expired before completion.', updated_at = now()
        WHERE campaign_id = :campaign AND status = 'running'
          AND lease_expires_at < clock_timestamp()
        RETURNING id
    """,
        {"campaign": campaign_id},
    )
    return await fetch(
        session,
        """
        WITH available AS (
          SELECT id FROM sync_work_item WHERE campaign_id = :campaign AND status = 'queued'
            AND (next_retry_at IS NULL OR next_retry_at <= clock_timestamp())
          ORDER BY shard, id FOR UPDATE SKIP LOCKED LIMIT :limit
        ) UPDATE sync_work_item item SET status = 'running', attempt = item.attempt + 1,
          started_at = now(), lease_owner = :owner,
          lease_expires_at = clock_timestamp() + make_interval(secs => :seconds), updated_at = now()
        FROM available WHERE item.id = available.id RETURNING item.*
    """,
        {
            "campaign": campaign_id,
            "owner": owner,
            "limit": max(0, limit),
            "seconds": max(1, lease_seconds),
        },
    )


async def owned_item(session: AsyncSession, item_id: UUID, owner: str) -> Any:
    # Controls and acknowledgements lock the campaign before its items.
    campaign = await fetch(
        session,
        """
        SELECT c.id, c.status FROM sync_campaign c JOIN sync_work_item i ON i.campaign_id = c.id
        WHERE i.id = :id FOR UPDATE OF c
    """,
        {"id": item_id},
    )
    if not campaign or campaign[0].status == "cancelled":
        raise LeaseLost("Campaign was cancelled or removed.")
    rows = await fetch(
        session,
        """
        SELECT * FROM sync_work_item WHERE id = :id AND status = 'running'
          AND lease_owner = :owner AND lease_expires_at > clock_timestamp() FOR UPDATE
    """,
        {"id": item_id, "owner": owner},
    )
    if not rows:
        raise LeaseLost("Work item lease expired or changed owner.")
    return rows[0]


async def succeed(session: AsyncSession, item_id: UUID, owner: str, result: dict[str, Any]) -> None:
    item = await owned_item(session, item_id, owner)
    await fetch(
        session,
        """
        UPDATE sync_work_item SET status = 'succeeded', result = CAST(:result AS jsonb),
          finished_at = now(), error = '', last_error_code = '', next_retry_at = NULL,
          lease_owner = '', lease_expires_at = NULL, updated_at = now()
        WHERE id = :id RETURNING id
    """,
        {"id": item_id, "result": json.dumps(result)},
    )
    await count_outcome(session, item.campaign_id, "succeeded")


async def fail(
    session: AsyncSession, item_id: UUID, owner: str, error: Exception, *, max_attempts: int = 5
) -> str:
    item = await owned_item(session, item_id, owner)
    failure = classify_failure(
        error, attempt=item.attempt, max_attempts=max_attempts, now=datetime.now(UTC)
    )
    await fetch(
        session,
        """
        UPDATE sync_work_item SET status = CAST(:status AS text), error = :error,
          last_error_code = :code,
          next_retry_at = :retry,
          finished_at = CASE WHEN CAST(:status AS text) = 'queued' THEN NULL ELSE now() END,
          lease_owner = '', lease_expires_at = NULL, updated_at = now() WHERE id = :id RETURNING id
    """,
        {
            "id": item_id,
            "status": failure.status,
            "error": failure.message,
            "code": failure.code,
            "retry": failure.next_retry_at,
        },
    )
    if failure.status != "queued":
        await count_outcome(session, item.campaign_id, failure.status)
    return failure.status


async def heartbeat(
    session: AsyncSession, item_id: UUID, owner: str, *, lease_seconds: int = 1200
) -> None:
    await owned_item(session, item_id, owner)
    rows = await fetch(
        session,
        "UPDATE sync_work_item SET lease_expires_at=clock_timestamp()+"
        "make_interval(secs=>:seconds),"
        "updated_at=now() WHERE id=:id AND lease_owner=:owner AND status='running' "
        "AND lease_expires_at>clock_timestamp() RETURNING id",
        {"id": item_id, "owner": owner, "seconds": lease_seconds},
    )
    if not rows:
        raise LeaseLost("Work item lease expired before renewal.")


async def count_outcome(session: AsyncSession, campaign_id: UUID, status: str) -> None:
    # The campaign/item locks and running-state guard make each terminal delta exactly once.
    await fetch(
        session,
        "UPDATE sync_campaign SET processed_items=processed_items+1,"
        "synced_items=synced_items+:synced,skipped_items=skipped_items+:skipped,"
        "failed_items=failed_items+:failed,updated_at=now() WHERE id=:id RETURNING id",
        {
            "id": campaign_id,
            "synced": int(status == "succeeded"),
            "skipped": int(status == "skipped"),
            "failed": int(status == "failed"),
        },
    )
