from unittest.mock import patch

import pytest

from apps.index.models import Entity, EntityName, ProviderRecord, Work
from apps.sync.providers.mal import MAL_ANIME_NAMESPACE, jikan_client
from apps.sync.services.mal_service import mal_import_service

pytestmark = pytest.mark.django_db(transaction=True)


def _anime_item() -> dict:
    return {
        "mal_id": 5114,
        "url": "https://myanimelist.net/anime/5114",
        "type": "TV",
        "title": "Hanasaku Iroha",
        "title_english": "Hanasaku Iroha",
        "title_japanese": "花咲くいろは",
        "title_synonyms": [],
        "titles": [
            {"type": "Default", "title": "Hanasaku Iroha"},
            {"type": "Japanese", "title": "花咲くいろは"},
            {"type": "English", "title": "Hanasaku Iroha"},
        ],
        "status": "Finished Airing",
        "episodes": 26,
        "duration": "24 min per ep",
        "score": 7.9,
        "rank": 300,
        "popularity": 100,
        "members": 10000,
        "favorites": 20,
        "season": "spring",
        "year": 2011,
        "synopsis": "Ohana is sent to live at a country inn.",
        "images": {
            "jpg": {
                "large_image_url": "https://cdn.myanimelist.net/large.jpg",
                "small_image_url": "https://cdn.myanimelist.net/small.jpg",
            },
            "webp": {},
        },
        "aired": {
            "from": "2011-04-03T00:00:00+09:00",
            "to": "2011-09-25T00:00:00+09:00",
        },
        "broadcast": {
            "day": "Sundays",
            "time": "22:00",
            "timezone": "Asia/Tokyo",
        },
    }


def test_persist_anime_creates_bounded_mal_entity() -> None:
    entity = mal_import_service._persist_anime(_anime_item())

    assert entity.kind == Entity.Kind.WORK
    work = Work.objects.get(entity=entity)
    assert work.work_type == Work.WorkType.ANIME
    assert work.anime_profile.episode_count == 26
    record = ProviderRecord.objects.get(
        namespace__provider__slug="mal",
        namespace__slug=MAL_ANIME_NAMESPACE.slug,
        external_id="5114",
    )
    assert record.representations.filter(entity=entity, is_active=True).exists()
    texts = set(EntityName.objects.filter(entity=entity).values_list("text", flat=True))
    assert {"Hanasaku Iroha", "花咲くいろは"} <= texts
    assert entity.facts.filter(predicate__slug="broadcast-time").exists()
    assert entity.facts.filter(predicate__slug="release-date").exists()


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
        jikan_client,
        "fetch_anime_full",
        return_value=_anime_item(),
    ) as fetch:
        entity = mal_import_service.import_anime(5114)

    fetch.assert_called_once_with(5114)
    assert entity.kind == Entity.Kind.WORK
