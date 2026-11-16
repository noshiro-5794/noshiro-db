"""Persist one bounded discovery step without losing cursor progress on retries."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.campaigns import get_campaign
from api.contexts.synchronization.discovery import discover_page
from api.contexts.synchronization.domain import LeaseLost
from api.contexts.synchronization.work_items import enqueue_page
from api.worker.providers.catalog import DeltaPage


def positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def accumulate_watermark(previous: str | None, value: str) -> str | None:
    if not value.isdigit():
        return previous
    return str(max(int(previous or 0), int(value)))


async def discover_step(session: AsyncSession, campaign_id: UUID, owner: str) -> bool:
    campaign = await get_campaign(session, campaign_id)
    count = positive_int((campaign.parameters or {}).get("discovery_pages_per_step"), 1)
    for _ in range(count):
        campaign = await get_campaign(session, campaign_id)
        if campaign.status != "discovering":
            raise LeaseLost("Campaign is no longer discovering.")
        params = dict(campaign.parameters or {})
        discovery = dict(params.get("discovery") or {})
        if discovery.get("pages") and not discovery.get("next_cursor"):
            return True
        cursor = discovery.get("next_cursor")
        delta = campaign.campaign_type == "incremental"
        page = await discover_page(
            session,
            campaign.provider_slug,
            cursor=cursor,
            page_size=positive_int(params.get("page_size"), 100),
            watermark=str(params.get("watermark") or "0") if delta else None,
        )
        # The provider call does not hold a campaign lock. Check ownership and controls
        # again before atomically recording both the page and its next cursor.
        rows = await fetch(
            session,
            """
            SELECT * FROM sync_campaign WHERE id = :id AND status = 'discovering'
              AND lease_owner = :owner AND lease_expires_at > clock_timestamp() FOR UPDATE
        """,
            {"id": campaign_id, "owner": owner},
        )
        if not rows:
            raise LeaseLost("Campaign lease or status changed during discovery.")
        latest = dict(rows[0].parameters or {})
        if latest != params:
            raise LeaseLost("Campaign parameters changed during the provider call.")
        pages = int(discovery.get("pages") or 0) + 1
        await enqueue_page(session, campaign_id, pages, list(page.external_ids))
        discovery.update(next_cursor=page.next_cursor, pages=pages)
        if delta and isinstance(page, DeltaPage):
            pending = accumulate_watermark(params.get("pending_watermark"), page.watermark)
            if pending is not None:
                params["pending_watermark"] = pending
                window = positive_int(params.get("delta_window_pages"), 80)
                if (
                    page.next_cursor
                    and pages % window == 0
                    and int(pending) > int(params.get("watermark") or "0")
                ):
                    params["watermark"] = pending
                    params.pop("pending_watermark", None)
                    discovery["next_cursor"] = "1"
        maximum = params.get("max_pages")
        if maximum is not None and pages >= positive_int(maximum, pages):
            discovery["truncated"] = bool(discovery["next_cursor"])
            discovery["next_cursor"] = None
            params.pop("pending_watermark", None)
        params["discovery"] = discovery
        await fetch(
            session,
            """
            UPDATE sync_campaign SET parameters = CAST(:params AS jsonb),
              total_items = (SELECT count(*) FROM sync_work_item WHERE campaign_id = :id),
              heartbeat_at = now(), updated_at = now() WHERE id = :id RETURNING id
        """,
            {"id": campaign_id, "params": json.dumps(params)},
        )
        await session.commit()
        if not discovery["next_cursor"]:
            return True
    return False
