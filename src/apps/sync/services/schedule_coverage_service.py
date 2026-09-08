"""Read-only schedule coverage report for Bangumi, AniList, and MAL."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.index.models import (
    AiringBoard,
    AiringBoardEntry,
    AiringEvent,
    Entity,
    ProviderRecord,
    ProviderRepresentation,
)

SUPPORTED_SOURCES = ("bangumi", "anilist", "mal")


class ScheduleCoverageService:
    def report(self) -> dict[str, Any]:
        season_key = self._current_season_key()
        return {
            "season_key": season_key,
            "sources": {
                "bangumi": self._bangumi_coverage(),
                "anilist": self._anilist_coverage(),
                "mal": self._mal_coverage(),
            },
            "identity": self._identity_coverage(),
            "board_projection": self._board_projection_coverage(),
            "generated_at": timezone.now().isoformat(),
        }

    @staticmethod
    def _current_season_key() -> str:
        now = timezone.localtime()
        return f"{now.year}Q{(now.month - 1) // 3 + 1}"

    @staticmethod
    def _bangumi_coverage() -> dict[str, Any]:
        board = (
            AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE)
            .select_related("observation")
            .first()
        )
        item_count = 0
        if board is not None and board.observation_id is not None:
            item_count = (
                AiringEvent.objects.filter(observation_id=board.observation_id)
                .values("work_id")
                .distinct()
                .count()
            )
        record_count = ProviderRecord.objects.filter(
            namespace__provider__slug="bangumi",
            namespace__slug="calendar",
            status=ProviderRecord.Status.ACTIVE,
        ).count()
        return {
            "record_count": record_count,
            "board_item_count": item_count,
        }

    @staticmethod
    def _anilist_coverage() -> dict[str, Any]:
        item_ids = set(
            ProviderRecord.objects.filter(
                namespace__provider__slug="anilist",
                namespace__slug="season-item",
                status=ProviderRecord.Status.ACTIVE,
            ).values_list("external_id", flat=True)
        )
        return {
            "item_count": len(item_ids),
            "schedule_observation_records": ProviderRecord.objects.filter(
                namespace__provider__slug="anilist",
                namespace__slug__in=("calendar", "season"),
                status=ProviderRecord.Status.ACTIVE,
            ).count(),
        }

    @staticmethod
    def _mal_coverage() -> dict[str, Any]:
        item_ids = set(
            ProviderRecord.objects.filter(
                namespace__provider__slug="mal",
                namespace__slug="schedule-item",
                status=ProviderRecord.Status.ACTIVE,
            ).values_list("external_id", flat=True)
        )
        return {
            "item_count": len(item_ids),
            "schedule_observation_records": ProviderRecord.objects.filter(
                namespace__provider__slug="mal",
                namespace__slug__in=("schedule", "season"),
                status=ProviderRecord.Status.ACTIVE,
            ).count(),
        }

    @staticmethod
    def _identity_coverage() -> dict[str, Any]:
        rows = (
            ProviderRepresentation.objects.filter(
                is_active=True,
                provider_record__namespace__provider__slug__in=SUPPORTED_SOURCES,
                provider_record__status=ProviderRecord.Status.ACTIVE,
                entity__kind=Entity.Kind.WORK,
                entity__lifecycle=Entity.Lifecycle.ACTIVE,
            )
            .values("entity_id", "provider_record__namespace__provider__slug")
            .distinct()
        )
        per_entity: dict[Any, set[str]] = {}
        for row in rows:
            per_entity.setdefault(row["entity_id"], set()).add(
                row["provider_record__namespace__provider__slug"]
            )
        multisource = [
            str(entity_id)
            for entity_id, providers in per_entity.items()
            if len(providers) >= 2
        ]
        return {
            "source_linked_entities": len(per_entity),
            "multisource_entities": len(multisource),
        }

    @staticmethod
    def _board_projection_coverage() -> dict[str, Any]:
        board = AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE).first()
        if board is None:
            return {"active": False, "entry_count": 0}
        return {
            "active": True,
            "entry_count": AiringBoardEntry.objects.filter(board=board).count(),
        }


schedule_coverage_service = ScheduleCoverageService()
