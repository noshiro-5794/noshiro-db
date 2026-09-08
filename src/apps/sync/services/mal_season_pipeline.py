"""End-to-end current-season MAL pipeline for schedule and identity refresh."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.index.models import Entity, ProviderRecord, ProviderRepresentation
from apps.index.services import (
    airing_board_projection_service,
    mal_identity_service,
    provider_candidate_service,
)
from apps.sync.providers.mal import MAL_SCHEDULE_ITEM_NAMESPACE
from apps.sync.services.mal_schedule_service import mal_schedule_service


class MALSeasonPipelineService:
    """Fetch schedules, promote saved records, and reconcile identities."""

    def run(
        self,
        *,
        sync_schedules: bool = True,
        evaluate: bool = False,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        schedule_summary = mal_schedule_service.sync() if sync_schedules else None
        saved_ids = self._saved_anime_ids(max_items=max_items)
        imported = [
            str(entity.id)
            for external_id in saved_ids
            if (entity := self._import_one(external_id)) is not None
        ]
        identity_summary = mal_identity_service.reconcile_official_links()
        candidate_summary = provider_candidate_service.generate_mal_bangumi_candidates()
        created_ids = list(candidate_summary["created_ids"])
        board_summary = airing_board_projection_service.rebuild()
        if evaluate and created_ids:
            self._dispatch_ai_evaluations(created_ids)
        return {
            "schedule": schedule_summary,
            "saved_anime_ids": len(saved_ids),
            "imported_entities": len(imported),
            "identity": identity_summary,
            "mal_candidates": candidate_summary,
            "board_projection": board_summary,
            "ai_evaluations_dispatched": len(created_ids) if evaluate else 0,
        }

    @staticmethod
    def _saved_anime_ids(*, max_items: int | None) -> list[str]:
        records = (
            ProviderRecord.objects.filter(
                namespace__provider__slug=MAL_SCHEDULE_ITEM_NAMESPACE.source.slug,
                namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
                status=ProviderRecord.Status.ACTIVE,
                latest_revision__isnull=False,
            )
            .order_by("external_id")
            .values_list("external_id", flat=True)
            .distinct()
        )
        if max_items:
            return list(records[: max(1, int(max_items))])
        return list(records)

    @staticmethod
    @transaction.atomic
    def _import_one(external_id: str) -> Entity | None:
        from apps.sync.services.mal_service import mal_import_service

        representation = (
            ProviderRepresentation.objects.filter(
                provider_record__namespace__provider__slug=(
                    MAL_SCHEDULE_ITEM_NAMESPACE.source.slug
                ),
                provider_record__namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
                provider_record__external_id=external_id,
                provider_record__status=ProviderRecord.Status.ACTIVE,
                is_active=True,
            )
            .select_related("entity")
            .first()
        )
        if representation is not None:
            return representation.entity
        try:
            return mal_import_service.import_saved_anime(int(external_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _dispatch_ai_evaluations(candidate_ids: list[str]) -> None:
        from config.celery import app as celery_app

        for candidate_id in candidate_ids:
            celery_app.send_task(
                "apps.ai.tasks.evaluate_match_candidate_task",
                args=[candidate_id],
                queue="ai",
            )


mal_season_pipeline_service = MALSeasonPipelineService()
