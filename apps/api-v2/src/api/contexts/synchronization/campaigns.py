"""Transactional campaign creation, state transitions and lease ownership."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.domain import ACTIVE, TERMINAL, TRANSITIONS, UnsupportedAction


async def get_campaign(
    session: AsyncSession, campaign_id: str | UUID, *, lock: bool = False
) -> Any:
    try:
        identifier = UUID(str(campaign_id))
    except ValueError as error:
        raise LookupError("Sync campaign not found.") from error
    rows = await fetch(
        session,
        "SELECT * FROM sync_campaign WHERE id = :id" + (" FOR UPDATE" if lock else ""),
        {"id": identifier},
    )
    if not rows:
        raise LookupError("Sync campaign not found.")
    return rows[0]


async def create_campaign(
    session: AsyncSession,
    *,
    provider: str,
    campaign_type: str = "full",
    ai_mode: str = "shadow",
    parameters: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> UUID:
    if provider not in {"bangumi", "anilist", "mal", "vndb"}:
        raise ValueError("Unsupported sync provider.")
    if campaign_type not in {"full", "incremental"}:
        raise ValueError("Unsupported campaign type.")
    if ai_mode not in {"off", "shadow", "assisted", "required"}:
        raise ValueError("Unsupported AI mode.")
    key = idempotency_key.strip()[:128]
    rows = await fetch(
        session,
        """
        INSERT INTO sync_campaign (id, provider_slug, campaign_type, status, ai_mode, parameters,
          total_items, processed_items, synced_items, skipped_items, failed_items, error,
          created_at, updated_at, idempotency_key, lease_owner)
        VALUES (:id, :provider, :type, 'queued', :mode, CAST(:parameters AS jsonb),
          0, 0, 0, 0, 0, '', now(), now(), :key, '')
        ON CONFLICT (provider_slug, campaign_type, idempotency_key) WHERE idempotency_key <> ''
        DO NOTHING RETURNING id
    """,
        {
            "id": uuid4(),
            "provider": provider,
            "type": campaign_type,
            "mode": ai_mode,
            "parameters": json.dumps(parameters or {}),
            "key": key,
        },
    )
    if rows:
        return UUID(str(rows[0].id))
    rows = await fetch(
        session,
        """
        SELECT id FROM sync_campaign WHERE provider_slug = :provider
          AND campaign_type = :type AND idempotency_key = :key
    """,
        {"provider": provider, "type": campaign_type, "key": key},
    )
    return UUID(str(rows[0].id))


async def transition(
    session: AsyncSession, campaign_id: UUID, previous: str, following: str
) -> bool:
    if (previous, following) not in TRANSITIONS:
        return False
    rows = await fetch(
        session,
        """
        UPDATE sync_campaign SET status = CAST(:following AS text), updated_at = now(),
          started_at = CASE WHEN CAST(:previous AS text) = 'queued' THEN now() ELSE started_at END,
          finished_at = CASE WHEN CAST(:following AS text) IN ('completed','failed','cancelled')
                            THEN now() ELSE finished_at END
        WHERE id = :id AND status = CAST(:previous AS text) RETURNING id
    """,
        {"id": campaign_id, "previous": previous, "following": following},
    )
    return bool(rows)


async def claim_campaign(
    session: AsyncSession, campaign_id: UUID, owner: str, *, lease_seconds: int = 600
) -> Any | None:
    rows = await fetch(
        session,
        """
        UPDATE sync_campaign SET lease_owner = :owner,
          lease_expires_at = clock_timestamp() + make_interval(secs => :seconds),
          heartbeat_at = clock_timestamp()
        WHERE id = :id AND status <> ALL(:terminal)
          AND (lease_expires_at IS NULL OR lease_expires_at < clock_timestamp()) RETURNING *
    """,
        {
            "id": campaign_id,
            "owner": owner,
            "seconds": max(1, lease_seconds),
            "terminal": sorted(TERMINAL),
        },
    )
    return rows[0] if rows else None


async def heartbeat(
    session: AsyncSession, campaign_id: UUID, owner: str, *, lease_seconds: int = 600
) -> bool:
    rows = await fetch(
        session,
        """
        UPDATE sync_campaign SET heartbeat_at = now(),
          lease_expires_at = clock_timestamp() + make_interval(secs => :seconds)
        WHERE id = :id AND lease_owner = :owner AND lease_expires_at > clock_timestamp()
        RETURNING id
    """,
        {"id": campaign_id, "owner": owner, "seconds": max(1, lease_seconds)},
    )
    return bool(rows)


async def release(session: AsyncSession, campaign_id: UUID, owner: str) -> bool:
    rows = await fetch(
        session,
        """
        UPDATE sync_campaign SET lease_owner = '', lease_expires_at = NULL, heartbeat_at = now()
        WHERE id = :id AND lease_owner = :owner RETURNING id
    """,
        {"id": campaign_id, "owner": owner},
    )
    return bool(rows)


async def control(session: AsyncSession, campaign_id: str, action: str) -> Any:
    row = await get_campaign(session, campaign_id, lock=True)
    parameters = dict(row.parameters or {})
    status = row.status
    if action == "pause":
        if status in ACTIVE:
            parameters["paused_from"] = status
            await fetch(
                session,
                """
                UPDATE sync_campaign SET status = 'paused', parameters = CAST(:params AS jsonb),
                  next_run_at = NULL, updated_at = now() WHERE id = :id RETURNING id
            """,
                {"id": row.id, "params": json.dumps(parameters)},
            )
    elif action == "resume":
        if status == "paused":
            previous = parameters.pop("paused_from", "discovering")
            previous = previous if previous in ACTIVE else "discovering"
            await fetch(
                session,
                """
                UPDATE sync_campaign SET status = :status, parameters = CAST(:params AS jsonb),
                  next_run_at = now(), updated_at = now() WHERE id = :id RETURNING id
            """,
                {"id": row.id, "status": previous, "params": json.dumps(parameters)},
            )
    elif action == "cancel":
        if status not in {"completed", "cancelled"}:
            await fetch(
                session,
                """
                UPDATE sync_campaign SET status = 'cancelled', finished_at = now(),
                  next_run_at = NULL, updated_at = now() WHERE id = :id RETURNING id
            """,
                {"id": row.id},
            )
            await fetch(
                session,
                """
                UPDATE sync_work_item SET status = 'queued', lease_owner = '',
                  lease_expires_at = NULL
                WHERE campaign_id = :id AND status = 'running' RETURNING id
            """,
                {"id": row.id},
            )
    else:
        raise UnsupportedAction("Unsupported campaign action.")
    return await get_campaign(session, row.id)


async def resume_failed(session: AsyncSession, campaign_id: UUID) -> Any:
    row = await get_campaign(session, campaign_id, lock=True)
    if row.status != "failed":
        return row
    await fetch(
        session,
        """
        UPDATE sync_work_item SET status = 'queued', error = '', lease_owner = '',
          lease_expires_at = NULL, finished_at = NULL, next_retry_at = NULL, last_error_code = ''
        WHERE campaign_id = :id AND status = 'failed' RETURNING id
    """,
        {"id": campaign_id},
    )
    parameters = row.parameters or {}
    discovery = parameters.get("discovery") or {}
    following = (
        "discovering"
        if "discovery" not in parameters or discovery.get("next_cursor")
        else "fetching"
    )
    await fetch(
        session,
        """
        UPDATE sync_campaign SET status = :status, error = '', finished_at = NULL,
          updated_at = now() WHERE id = :id RETURNING id
    """,
        {"id": campaign_id, "status": following},
    )
    await refresh_counts(session, campaign_id)
    return await get_campaign(session, campaign_id)


async def refresh_counts(session: AsyncSession, campaign_id: UUID) -> None:
    await fetch(
        session,
        """
        UPDATE sync_campaign c SET
          processed_items = (SELECT count(*) FROM sync_work_item WHERE campaign_id = c.id
                             AND status IN ('succeeded','skipped','failed')),
          synced_items = (SELECT count(*) FROM sync_work_item
                          WHERE campaign_id = c.id AND status = 'succeeded'),
          skipped_items = (SELECT count(*) FROM sync_work_item
                           WHERE campaign_id = c.id AND status = 'skipped'),
          failed_items = (SELECT count(*) FROM sync_work_item
                          WHERE campaign_id = c.id AND status = 'failed'), updated_at = now()
        WHERE c.id = :id RETURNING id
    """,
        {"id": campaign_id},
    )
