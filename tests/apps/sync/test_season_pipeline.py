from unittest.mock import patch

import pytest

from apps.sync.services.season_pipeline_service import season_pipeline_service

pytestmark = pytest.mark.django_db(transaction=True)


def test_run_chains_anilist_promotion_candidates_and_mal_pipeline() -> None:
    with (
        patch.object(
            season_pipeline_service,
            "_generate_anilist_candidates",
            return_value={"created_ids": ["c1"]},
        ),
        patch.object(
            season_pipeline_service,
            "_dispatch_ai_evaluations",
        ) as dispatch,
        patch(
            "apps.sync.services.season_pipeline_service.anilist_season_service.sync_current_season",
            return_value={"season_key": "fall:2026"},
        ),
        patch(
            "apps.sync.services.season_pipeline_service.anilist_import_service.import_saved_media",
            return_value=type("Entity", (), {"id": "anilist-1"})(),
        ),
        patch(
            "apps.sync.services.season_pipeline_service.ProviderRecord.objects.filter",
        ) as records,
        patch(
            "apps.sync.services.season_pipeline_service.mal_season_pipeline_service.run",
            return_value={"identity": {"bound": 0}},
        ) as mal_run,
    ):
        records.return_value.order_by.return_value.values_list.return_value.distinct.return_value = [
            "189046"
        ]
        result = season_pipeline_service.run(
            max_items_per_source=2,
            evaluate=True,
        )

    assert result["anilist_imported"] == 1
    assert result["ai_evaluations_dispatched"] == 1
    mal_run.assert_called_once_with(
        sync_schedules=True,
        evaluate=False,
        max_items=2,
    )
    dispatch.assert_called_once_with(["c1"])
