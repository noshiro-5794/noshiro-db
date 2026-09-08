"""One-command season reconciliation across AniList, MAL, and Bangumi."""

from __future__ import annotations

from typing import Any

from apps.index.models import ProviderRecord
from apps.sync.providers.anilist import ANILIST_SEASON_ITEM_NAMESPACE
from apps.sync.services.anilist_season_service import anilist_season_service
from apps.sync.services.anilist_service import anilist_import_service
from apps.sync.services.mal_season_pipeline import mal_season_pipeline_service


class SeasonPipelineService:
    """Promote seasonal sources and reconcile their cross-provider identity."""

    def run(
        self,
        *,
        max_items_per_source: int | None = None,
        evaluate: bool = False,
    ) -> dict[str, Any]:
        anilist_snapshot = anilist_season_service.sync_current_season()
        anilist_imported = self._promote_anilist_records(max_items=max_items_per_source)
        anilist_candidates = self._generate_anilist_candidates()
        mal_result = mal_season_pipeline_service.run(
            sync_schedules=True,
            evaluate=False,
            max_items=max_items_per_source,
        )
        created_ids = list(anilist_candidates["created_ids"])
        if evaluate:
            self._dispatch_ai_evaluations(created_ids)
        return {
            "anilist_snapshot": anilist_snapshot,
            "anilist_imported": len(anilist_imported),
            "anilist_candidates": {
                "created": len(created_ids),
                "ids": created_ids,
            },
            "mal": mal_result,
            "ai_evaluations_dispatched": len(created_ids) if evaluate else 0,
        }

    @staticmethod
    def _promote_anilist_records(*, max_items: int | None) -> list[str]:
        external_ids = (
            ProviderRecord.objects.filter(
                namespace__provider__slug="anilist",
                namespace__slug=ANILIST_SEASON_ITEM_NAMESPACE.slug,
                status=ProviderRecord.Status.ACTIVE,
                latest_revision__isnull=False,
            )
            .order_by("external_id")
            .values_list("external_id", flat=True)
            .distinct()
        )
        if max_items:
            external_ids = external_ids[: max(1, int(max_items))]
        imported: list[str] = []
        for external_id in external_ids:
            try:
                entity = anilist_import_service.import_saved_media(int(external_id))
            except (TypeError, ValueError):
                continue
            if entity is not None:
                imported.append(str(entity.id))
        return imported

    @staticmethod
    def _generate_anilist_candidates() -> dict[str, Any]:
        from apps.index.services import provider_candidate_service

        return provider_candidate_service.generate_candidates(
            source_provider="anilist",
            source_namespace="anime",
            target_provider="bangumi",
            target_namespace="subject",
            min_similarity=0.6,
            top_k=5,
            create=True,
        )

    @staticmethod
    def _dispatch_ai_evaluations(candidate_ids: list[str]) -> None:
        from config.celery import app as celery_app

        for candidate_id in candidate_ids:
            celery_app.send_task(
                "apps.ai.tasks.evaluate_match_candidate_task",
                args=[candidate_id],
                queue="ai",
            )


season_pipeline_service = SeasonPipelineService()
