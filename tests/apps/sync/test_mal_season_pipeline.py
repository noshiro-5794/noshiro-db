from unittest.mock import patch

import pytest

from apps.index.models import (
    Entity,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    ProviderRevision,
    Work,
)
from apps.sync.providers.mal import MAL_SCHEDULE_ITEM_NAMESPACE
from apps.sync.services.mal_season_pipeline import mal_season_pipeline_service

pytestmark = pytest.mark.django_db(transaction=True)


def _schedule_item_record(*, mal_id: int = 5114) -> None:
    provider, _ = Provider.objects.get_or_create(
        slug="mal",
        defaults={"name": "MyAnimeList"},
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    payload = {
        "id": mal_id,
        "title": "Hanasaku Iroha",
        "alternative_titles": {
            "synonyms": [],
            "en": "Hanasaku Iroha",
            "ja": "花咲くいろは",
        },
        "media_type": "tv",
        "num_episodes": 26,
        "status": "currently_airing",
        "synopsis": "",
        "main_picture": {
            "medium": "https://example.test/medium.jpg",
            "large": "https://example.test/large.jpg",
        },
        "start_date": "2011-04-03",
        "end_date": "2011-09-25",
        "average_episode_duration": 1440,
    }
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=str(mal_id),
        origin="api",
        status="active",
    )
    revision = ProviderRevision.objects.create(
        record=record,
        payload=payload,
        payload_hash=f"payload-{mal_id}",
        schema_version="mal-api-v2",
    )
    ProviderRecord.objects.filter(pk=record.pk).update(latest_revision=revision)


def test_pipeline_promotes_saved_schedule_record_to_entity() -> None:
    _schedule_item_record()

    with patch(
        "apps.sync.services.mal_season_pipeline.provider_candidate_service.generate_mal_bangumi_candidates",
        return_value={"created_ids": [], "pairs": []},
    ) as candidates:
        result = mal_season_pipeline_service.run(
            fetch_season=False,
            evaluate=False,
        )

    assert result["season"] is None
    assert result["saved_anime_ids"] == 1
    assert result["imported_entities"] == 1
    assert result["identity"]["bound"] == 0
    candidates.assert_called_once()
    entity = Entity.objects.get(kind=Entity.Kind.WORK)
    work = Work.objects.get(entity=entity)
    assert work.work_type == Work.WorkType.ANIME
    assert (
        ProviderRepresentation.objects.filter(
            entity=entity,
            provider_record__namespace__slug="anime",
            provider_record__namespace__provider__slug="mal",
        ).exists()
        is True
    )
