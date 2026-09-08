from unittest.mock import patch

import pytest

from apps.index.models import Entity, EntityName, ProviderRecord, Work
from apps.sync.providers.mal import MAL_ANIME_NAMESPACE, mal_api_client
from apps.sync.services.mal_service import mal_import_service

pytestmark = pytest.mark.django_db(transaction=True)


def _anime_item() -> dict:
    return {
        "id": 5114,
        "title": "Hanasaku Iroha",
        "alternative_titles": {
            "synonyms": [],
            "en": "Hanasaku Iroha",
            "ja": "花咲くいろは",
        },
        "media_type": "tv",
        "status": "finished_airing",
        "num_episodes": 26,
        "average_episode_duration": 1440,
        "mean": 7.9,
        "rank": 300,
        "popularity": 100,
        "num_list_users": 10000,
        "start_season": {"year": 2011, "season": "spring"},
        "start_date": "2011-04-03",
        "end_date": "2011-09-25",
        "synopsis": "Ohana is sent to live at a country inn.",
        "main_picture": {
            "medium": "https://cdn.myanimelist.net/medium.jpg",
            "large": "https://cdn.myanimelist.net/large.jpg",
        },
        "broadcast": {
            "day_of_the_week": "sundays",
            "start_time": "22:00",
        },
        "source": "original",
        "rating": "pg_13",
        "pictures": [
            {
                "medium": "https://cdn.myanimelist.net/p1.jpg",
                "large": "https://cdn.myanimelist.net/p1l.jpg",
            }
        ],
        "studios": [{"id": 1, "name": "P.A. Works"}],
    }


def test_persist_anime_creates_bounded_mal_entity() -> None:
    entity = mal_import_service._persist_anime(_anime_item())

    assert entity.kind == Entity.Kind.WORK
    work = Work.objects.get(entity=entity)
    assert work.work_type == Work.WorkType.ANIME
    assert work.anime_profile.episode_count == 26
    assert work.anime_profile.format == "TV"
    record = ProviderRecord.objects.get(
        namespace__provider__slug="mal",
        namespace__slug=MAL_ANIME_NAMESPACE.slug,
        external_id="5114",
    )
    assert record.latest_revision.schema_version == "mal-api-v2"
    assert record.representations.filter(entity=entity, is_active=True).exists()
    texts = set(EntityName.objects.filter(entity=entity).values_list("text", flat=True))
    assert {"Hanasaku Iroha", "花咲くいろは"} <= texts
    assert entity.facts.filter(predicate__slug="broadcast-time").exists()
    assert entity.facts.filter(predicate__slug="release-date").exists()
    assert entity.facts.filter(predicate__slug="mal-status").exists()
    assert entity.facts.filter(predicate__slug="duration-minutes").exists()


def test_persist_anime_is_idempotent() -> None:
    first = mal_import_service._persist_anime(_anime_item())
    second = mal_import_service._persist_anime(_anime_item())

    assert first.id == second.id
    assert (
        ProviderRecord.objects.filter(
            namespace__provider__slug="mal",
            namespace__slug=MAL_ANIME_NAMESPACE.slug,
            external_id="5114",
        ).count()
        == 1
    )
    assert EntityName.objects.filter(entity=first).count() == 3


def test_import_anime_fetches_full_record() -> None:
    with patch.object(
        mal_api_client,
        "fetch_anime_full",
        return_value=_anime_item(),
    ) as fetch:
        entity = mal_import_service.import_anime(5114)

    fetch.assert_called_once_with(5114)
    assert entity.kind == Entity.Kind.WORK
