"""Multi-source weekly board projection (the Gantt-ready board layer).

``AiringEvent`` rows stay immutable per-source facts. This service rebuilds the
curated ``AiringBoardEntry`` window for the active board from those facts plus
MAL broadcast rules, after canonical identity resolution, so the calendar can
draw one bar per canonical work instead of per source.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from apps.index.models import (
    AiringBoard,
    AiringBoardEntry,
    AiringEvent,
    Entity,
    Observation,
    ProviderRepresentation,
    Work,
)
from apps.index.selectors.current import active_airing_board_events
from apps.index.services.airing_board import airing_board_service
from apps.index.services.resolution import entity_resolution_service

_WEEKDAY_MAP = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}

_MAL_DAY_LABELS = {
    "mondays": 1,
    "tuesdays": 2,
    "wednesdays": 3,
    "thursdays": 4,
    "fridays": 5,
    "saturdays": 6,
    "sundays": 7,
}

# MAL is the authoritative source for the current-season board: Jikan mirrors
# MAL's own broadcast data and this project treats MAL as the identity spine.
# AniList and Bangumi corroborate slots; when sources disagree on the same
# canonical work, the lower-priority source only appears if the leader is
# absent for that work/day.
_SOURCE_PRIORITY = {"mal": 0, "anilist": 1, "bangumi": 2}


@dataclass(frozen=True, slots=True)
class CandidateBar:
    """One source-supplied bar waiting for canonical deduplication."""

    entity_id: Any
    weekday: int
    starts_at: datetime | None = None
    timezone: str = ""
    duration_minutes: int | None = None
    episode_number: int | None = None
    precision: str = AiringBoardEntry.Precision.WEEKDAY
    status: str = AiringBoardEntry.Status.TENTATIVE
    provider: str = ""
    observation_id: Any = None
    external_id: str = ""


class AiringBoardProjectionService:
    def rebuild(self) -> dict[str, Any]:
        board = self._ensure_board()
        candidates = self._candidates_for_window()
        entries = self._project_candidates(candidates, board=board)
        with transaction.atomic():
            AiringBoardEntry.objects.filter(board=board).delete()
            if entries:
                AiringBoardEntry.objects.bulk_create(entries)
            airing_board_service.refresh(
                observation=board.observation,
                season_key=board.season_key,
                item_count=len(entries),
                metadata={
                    "projection": "multisource",
                    "candidate_count": len(candidates),
                    "generated_at": timezone.now().isoformat(),
                },
            )
        return {
            "board_id": str(board.id),
            "season_key": board.season_key,
            "entries": len(entries),
            "candidates": len(candidates),
        }

    @staticmethod
    def _ensure_board() -> AiringBoard:
        board = (
            AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE)
            .select_related("observation")
            .first()
        )
        if board is None:
            board = airing_board_service.refresh(
                observation=None,
                season_key="",
                item_count=0,
            )
        now = timezone.localtime()
        season_key = f"{now.year}Q{(now.month - 1) // 3 + 1}"
        if board.season_key != season_key:
            return airing_board_service.refresh(
                observation=board.observation,
                season_key=season_key,
                item_count=0,
            )
        return board

    def _candidates_for_window(self) -> list[CandidateBar]:
        now = timezone.now()
        end = now + timedelta(days=7)
        candidates: list[CandidateBar] = []
        candidates.extend(self._bangumi_weekday_candidates())
        candidates.extend(self._anilist_minute_candidates(now=now, end=end))
        candidates.extend(self._mal_broadcast_candidates(now=now, end=end))
        return candidates

    @staticmethod
    def _bangumi_weekday_candidates() -> list[CandidateBar]:
        bars: list[CandidateBar] = []
        for event in active_airing_board_events().filter(
            precision=AiringEvent.Precision.WEEKDAY
        ):
            root = _canonical_entity(event.work.entity)
            if root is None:
                continue
            bars.append(
                CandidateBar(
                    entity_id=root.id,
                    weekday=event.weekday,
                    precision=AiringBoardEntry.Precision.WEEKDAY,
                    provider="bangumi",
                    observation_id=event.observation_id,
                )
            )
        return bars

    @staticmethod
    def _anilist_minute_candidates(
        *,
        now: datetime,
        end: datetime,
    ) -> list[CandidateBar]:
        bars: list[CandidateBar] = []
        events = (
            AiringEvent.objects.filter(
                starts_at__gte=now,
                starts_at__lt=end,
                precision=AiringEvent.Precision.MINUTE,
                work__work_type=Work.WorkType.ANIME,
                observation__provider_record__namespace__provider__slug="anilist",
                observation__provider_record__namespace__slug="calendar",
            )
            .select_related("work__entity", "observation")
            .order_by("starts_at")
        )
        for event in events:
            root = _canonical_entity(event.work.entity)
            if root is None:
                continue
            bars.append(
                CandidateBar(
                    entity_id=root.id,
                    weekday=event.starts_at.weekday() + 1 if event.starts_at else None,
                    starts_at=event.starts_at,
                    timezone=event.timezone or "UTC",
                    precision=AiringBoardEntry.Precision.MINUTE,
                    status=AiringBoardEntry.Status.SCHEDULED,
                    provider="anilist",
                    observation_id=event.observation_id,
                )
            )
        return bars

    def _mal_broadcast_candidates(
        self,
        *,
        now: datetime,
        end: datetime,
    ) -> list[CandidateBar]:
        bars: list[CandidateBar] = []
        mal_works = self._mal_work_index()
        records = Observation.objects.filter(
            schema_name="index.schedule",
            current_projections__provider_record__namespace__provider__slug="mal",
            current_projections__provider_record__namespace__slug="schedule",
        )
        for observation in records.prefetch_related("current_projections"):
            normalized = observation.normalized_data or {}
            weekday_label = str(normalized.get("weekday") or "").lower()
            weekday = _WEEKDAY_MAP.get(weekday_label)
            if weekday is None:
                continue
            for page in normalized.get("pages") or []:
                if not isinstance(page, dict):
                    continue
                for item in page.get("data") or []:
                    if not isinstance(item, dict):
                        continue
                    mal_id = item.get("mal_id")
                    if not isinstance(mal_id, int):
                        continue
                    bar = self._mal_item_bar(
                        item=item,
                        fallback_weekday=weekday,
                        mal_works=mal_works,
                        observation_id=observation.id,
                        now=now,
                        end=end,
                    )
                    if bar is not None:
                        bars.append(bar)
        return bars

    @staticmethod
    def _mal_item_bar(
        *,
        item: dict[str, Any],
        fallback_weekday: int,
        mal_works: dict[int, Any],
        observation_id: Any,
        now: datetime,
        end: datetime,
    ) -> CandidateBar | None:
        mal_id = item.get("mal_id")
        if not isinstance(mal_id, int):
            return None
        entity_id = mal_works.get(mal_id)
        if entity_id is None:
            return None
        broadcast = (
            item.get("broadcast") if isinstance(item.get("broadcast"), dict) else {}
        )
        weekday = _MAL_DAY_LABELS.get(
            str(broadcast.get("day") or "").strip().lower(),
            fallback_weekday,
        )
        if weekday is None:
            return None
        raw_time = broadcast.get("time")
        timezone_name = str(broadcast.get("timezone") or "Asia/Tokyo")
        starts_at = None
        if isinstance(raw_time, str) and ":" in raw_time:
            try:
                hour, minute = raw_time.split(":", 1)
                slot = _next_occurrence(
                    weekday=weekday,
                    hour=int(hour),
                    minute=int(minute[:2]),
                    timezone_name=timezone_name,
                    now=now,
                )
                starts_at = slot
            except ValueError:
                starts_at = None
        if starts_at is not None and not (now <= starts_at < end):
            return None
        duration = _duration_minutes(item.get("duration"))
        status = (
            AiringBoardEntry.Status.SCHEDULED
            if str(item.get("status") or "").lower() == "currently airing"
            else AiringBoardEntry.Status.TENTATIVE
        )
        return CandidateBar(
            entity_id=entity_id,
            weekday=weekday,
            starts_at=starts_at,
            timezone=timezone_name,
            duration_minutes=duration,
            precision=(
                AiringBoardEntry.Precision.MINUTE
                if starts_at is not None
                else AiringBoardEntry.Precision.WEEKDAY
            ),
            status=status,
            provider="mal",
            observation_id=observation_id,
            external_id=str(mal_id),
        )

    @staticmethod
    def _mal_work_index() -> dict[int, Any]:
        rows = (
            ProviderRepresentation.objects.filter(
                is_active=True,
                provider_record__namespace__provider__slug="mal",
                provider_record__namespace__slug="anime",
                entity__lifecycle=Entity.Lifecycle.ACTIVE,
            )
            .select_related("entity")
            .values_list("provider_record__external_id", "entity_id")
        )
        index: dict[int, Any] = {}
        for external_id, entity_id in rows:
            try:
                index[int(external_id)] = entity_id
            except (TypeError, ValueError):
                continue
        return index

    @staticmethod
    def _project_candidates(
        candidates: list[CandidateBar],
        *,
        board: AiringBoard,
    ) -> list[AiringBoardEntry]:
        grouped: dict[tuple[Any, int], list[CandidateBar]] = {}
        for bar in candidates:
            if bar.weekday is None:
                continue
            grouped.setdefault((bar.entity_id, bar.weekday), []).append(bar)
        entries: list[AiringBoardEntry] = []
        for (entity_id, weekday), bars in grouped.items():
            work = Work.objects.filter(entity_id=entity_id).first()
            if work is None:
                continue
            chosen = min(bars, key=lambda bar: _SOURCE_PRIORITY.get(bar.provider, 99))
            agrees = [
                bar
                for bar in bars
                if bar.provider != chosen.provider
                and bar.starts_at is not None
                and chosen.starts_at is not None
                and abs((bar.starts_at - chosen.starts_at).total_seconds()) <= 1800
            ]
            source_refs = [
                {
                    "provider": bar.provider,
                    "namespace": (
                        "subject"
                        if bar.provider == "bangumi"
                        else "anime"
                        if bar.provider == "mal"
                        else "calendar"
                    ),
                    "external_id": bar.external_id,
                    "observation_id": str(bar.observation_id)
                    if bar.observation_id
                    else "",
                }
                for bar in [chosen, *agrees]
            ]
            entries.append(
                AiringBoardEntry(
                    board=board,
                    work=work,
                    weekday=weekday,
                    starts_at=chosen.starts_at,
                    timezone=chosen.timezone,
                    duration_minutes=chosen.duration_minutes,
                    precision=chosen.precision,
                    status=chosen.status,
                    decision=(
                        AiringBoardEntry.Decision.CONSENSUS
                        if agrees
                        else AiringBoardEntry.Decision.SOURCE_PRIORITY
                    ),
                    confidence=(Decimal("1.0000") if agrees else Decimal("0.9500")),
                    source_refs=source_refs,
                )
            )
        return entries


airing_board_projection_service = AiringBoardProjectionService()


def _canonical_entity(entity: Entity) -> Entity | None:
    if entity.kind != Entity.Kind.WORK:
        return None
    root = entity_resolution_service.resolve(entity)
    if (
        root.lifecycle != Entity.Lifecycle.ACTIVE
        or not Work.objects.filter(entity=root).exists()
    ):
        return None
    return root


def _next_occurrence(
    *,
    weekday: int,
    hour: int,
    minute: int,
    timezone_name: str,
    now: datetime,
) -> datetime | None:
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = ZoneInfo("Asia/Tokyo")
    local_now = now.astimezone(zone)
    days_ahead = (weekday - local_now.isoweekday()) % 7
    local_slot = datetime.combine(
        local_now.date() + timedelta(days=days_ahead),
        time(hour=hour, minute=minute),
        tzinfo=zone,
    )
    if local_slot <= local_now:
        local_slot += timedelta(days=7)
    return local_slot.astimezone(UTC)


def _duration_minutes(raw: Any) -> int | None:
    if not isinstance(raw, str):
        return None
    for token in raw.split():
        if token.isdigit():
            return int(token)
    return None
