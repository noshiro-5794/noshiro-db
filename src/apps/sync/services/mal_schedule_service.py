"""Durable schedule persistence for MAL data fetched through Jikan.

The service keeps two complementary artifacts:

* point-in-time schedule observations under ``mal/season`` and ``mal/schedule``
  so board refreshes can compare source snapshots;
* one idempotent ``mal/anime`` provider record per MAL anime so identity
  matching can bind MAL ids to canonical entities without re-fetching pages.

The MAL anime rows created here are intentionally observation-free until a
detail import runs; the board and identity phases only need stable records.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.timezone import localdate

from apps.sync.providers.contracts import FetchedSourceRecord
from apps.sync.providers.mal import (
    JIKAN_WEEKDAYS,
    MAL_ANIME_NAMESPACE,
    MAL_SCHEDULE_NAMESPACE,
    MAL_SEASON_NAMESPACE,
    jikan_client,
)
from apps.sync.services.source_record_service import source_record_service
from apps.sync.services.sync_job_service import sync_job_service


class MALScheduleService:
    """Fetch and record the MAL weekly schedule and current season list."""

    WEEKDAYS = JIKAN_WEEKDAYS[:7]
    TASK_NAME = "mal_schedule"
    DEFAULT_PAGE_SIZE = 25
    DEFAULT_MAX_PAGES_PER_DAY = 20

    def sync(
        self,
        *,
        job_id: str | None = None,
        page_size: int | None = None,
        max_pages_per_weekday: int | None = None,
    ) -> dict[str, Any]:
        page_size = max(1, int(page_size or self.DEFAULT_PAGE_SIZE))
        max_pages = max(1, int(max_pages_per_weekday or self.DEFAULT_MAX_PAGES_PER_DAY))
        sync_job_service.mark_running(
            job_id=job_id,
            total_count=1 + len(self.WEEKDAYS),
            current_label="Fetching MAL season and weekly schedules",
        )
        try:
            season = self.sync_season_now(page_size=page_size, max_pages=max_pages)
            schedules = [
                self.sync_schedule_day(
                    weekday=weekday,
                    page_size=page_size,
                    max_pages=max_pages,
                )
                for weekday in self.WEEKDAYS
            ]
        except Exception as exc:
            sync_job_service.mark_failed(
                job_id=job_id,
                error=exc,
                current_label="MAL schedule sync failed",
            )
            raise
        result = {
            "source": "mal",
            "season": season,
            "weekday_schedules": schedules,
            "fetched_at": timezone.now().isoformat(),
        }
        sync_job_service.mark_succeeded(
            job_id=job_id,
            result=result,
            current_label="MAL schedule sync completed",
        )
        return result

    def sync_season_now(
        self,
        *,
        page_size: int = 25,
        max_pages: int = 20,
    ) -> dict[str, Any]:
        today = localdate()
        quarter = (today.month - 1) // 3 + 1
        season_key = f"{today.year}Q{quarter}"
        pages: list[dict[str, Any]] = []
        item_payloads: dict[str, dict[str, Any]] = {}
        next_cursor: str | None = None
        page_count = 0
        while page_count < max_pages:
            page_count += 1
            payload = jikan_client.fetch_season_now(
                cursor=next_cursor,
                page_size=page_size,
            )
            pages.append(payload)
            for item in self._items(payload):
                mal_id = item.get("mal_id")
                if isinstance(mal_id, int):
                    item_payloads[str(mal_id)] = item
            pagination = payload.get("pagination") if isinstance(payload, dict) else {}
            if (
                not isinstance(pagination, dict)
                or pagination.get("has_next_page") is not True
            ):
                break
            next_cursor = str(page_count + 1)

        recorded = self._record_season_pages(
            season_key=season_key,
            pages=pages,
        )
        item_ids = self._record_anime_items(item_payloads)
        return {
            "season_key": season_key,
            "pages": len(pages),
            "schedule_record_id": str(recorded.record.id),
            "changed": recorded.changed,
            "items_seen": len(item_payloads),
            "items_recorded": len(item_ids),
        }

    def sync_schedule_day(
        self,
        *,
        weekday: str,
        page_size: int = 25,
        max_pages: int = 20,
    ) -> dict[str, Any]:
        pages: list[dict[str, Any]] = []
        item_payloads: dict[str, dict[str, Any]] = {}
        next_cursor: str | None = None
        page_count = 0
        while page_count < max_pages:
            page_count += 1
            payload = jikan_client.fetch_schedule(
                weekday=weekday,
                cursor=next_cursor,
                page_size=page_size,
            )
            pages.append(payload)
            for item in self._items(payload):
                mal_id = item.get("mal_id")
                if isinstance(mal_id, int):
                    item_payloads[str(mal_id)] = item
            pagination = payload.get("pagination") if isinstance(payload, dict) else {}
            if (
                not isinstance(pagination, dict)
                or pagination.get("has_next_page") is not True
            ):
                break
            next_cursor = str(page_count + 1)

        recorded = source_record_service.record(
            namespace_spec=MAL_SCHEDULE_NAMESPACE,
            fetched=FetchedSourceRecord(
                external_id=f"weekly:{weekday}",
                payload={
                    "weekday": weekday,
                    "pages": pages,
                },
                canonical_url=(f"https://api.jikan.moe/v4/schedules?filter={weekday}"),
                schema_version="jikan-v4",
                mapper_version="mal-schedule-v1",
                fetched_at=timezone.now(),
            ),
        )
        item_ids = self._record_anime_items(item_payloads)
        return {
            "weekday": weekday,
            "pages": len(pages),
            "schedule_record_id": str(recorded.record.id),
            "changed": recorded.changed,
            "items_seen": len(item_payloads),
            "items_recorded": len(item_ids),
        }

    @staticmethod
    def _record_season_pages(
        *,
        season_key: str,
        pages: list[dict[str, Any]],
    ) -> Any:
        return source_record_service.record(
            namespace_spec=MAL_SEASON_NAMESPACE,
            fetched=FetchedSourceRecord(
                external_id=f"season-now:{season_key}",
                payload={
                    "season_key": season_key,
                    "pages": pages,
                },
                canonical_url="https://api.jikan.moe/v4/seasons/now",
                schema_version="jikan-v4",
                mapper_version="mal-season-v1",
                fetched_at=timezone.now(),
            ),
        )

    @staticmethod
    def _record_anime_items(items: dict[str, dict[str, Any]]) -> list[str]:
        if not items:
            return []
        fetched_records = [
            FetchedSourceRecord(
                external_id=external_id,
                payload=payload,
                canonical_url=(f"https://myanimelist.net/anime/{external_id}"),
                schema_version="jikan-v4",
                mapper_version="mal-schedule-item-v1",
                fetched_at=timezone.now(),
            )
            for external_id, payload in items.items()
        ]
        recorded = source_record_service.record_many(
            namespace_spec=MAL_ANIME_NAMESPACE,
            fetched_records=fetched_records,
        )
        return [
            str(item.record.id)
            for external_id in items
            if (item := recorded.get(external_id)) is not None
        ]

    @staticmethod
    def _items(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        return (
            [item for item in data if isinstance(item, dict)]
            if isinstance(data, list)
            else []
        )


mal_schedule_service = MALScheduleService()
