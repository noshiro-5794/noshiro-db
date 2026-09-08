from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.index.models import (
    AiringBoard,
    AiringBoardEntry,
    Entity,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services import (
    airing_board_projection_service,
    knowledge_ingestion_service,
)
from apps.sync.providers.contracts import (
    CatalogSourceSpec,
    FetchedSourceRecord,
    SourceNamespaceSpec,
)
from apps.sync.services.source_record_service import source_record_service

pytestmark = pytest.mark.django_db(transaction=True)


def _anime_entity(
    *, provider_slug: str, namespace_slug: str, external_id: str
) -> Entity:
    provider, _ = Provider.objects.get_or_create(
        slug=provider_slug,
        defaults={"name": provider_slug.title()},
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug=namespace_slug,
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        origin="api",
        status="active",
    )
    entity = Entity.objects.create(kind=Entity.Kind.WORK)
    Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
    ProviderRepresentation.objects.create(
        provider_record=record,
        entity=entity,
        mapping_kind=ProviderRepresentation.MappingKind.EXACT,
        method=ProviderRepresentation.Method.PROVIDER,
    )
    return entity


def test_rebuild_projects_mal_schedule_onto_one_board_entry() -> None:
    entity = _anime_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="5114",
    )
    source = CatalogSourceSpec(
        slug="mal",
        name="MyAnimeList",
        base_url="https://myanimelist.net",
    )
    schedule_namespace = SourceNamespaceSpec(
        source=source,
        slug="schedule",
        resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    )
    now = timezone.now().astimezone(ZoneInfo("Asia/Tokyo"))
    tomorrow = (now + timedelta(days=1)).strftime("%A").lower() + "s"
    payload_page = {
        "data": [
            {
                "mal_id": 5114,
                "title": "Hanasaku Iroha",
                "status": "Currently Airing",
                "episodes": 26,
                "duration": "24 min per ep",
                "broadcast": {
                    "day": tomorrow,
                    "time": "22:00",
                    "timezone": "Asia/Tokyo",
                },
            }
        ]
    }
    recorded = source_record_service.record(
        namespace_spec=schedule_namespace,
        fetched=FetchedSourceRecord(
            external_id="weekly:sunday",
            payload={"weekday": "sunday", "pages": [payload_page]},
            schema_version="jikan-v4",
            mapper_version="mal-schedule-v1",
        ),
    )
    knowledge_ingestion_service.record_observation(
        provider_record=recorded.record,
        mapper="mal.weekly",
        mapper_version="mal-schedule-v1",
        normalized_data={"weekday": "sunday", "pages": [payload_page]},
        schema_name="index.schedule",
        schema_version="1",
    )

    summary = airing_board_projection_service.rebuild()

    assert summary["entries"] == 1
    board = AiringBoard.objects.get(status=AiringBoard.Status.ACTIVE)
    entry = AiringBoardEntry.objects.get(board=board)
    assert entry.work_id == entity.id
    assert entry.precision == AiringBoardEntry.Precision.MINUTE
    assert entry.status == AiringBoardEntry.Status.SCHEDULED
    assert entry.source_refs[0]["provider"] == "mal"


def test_board_endpoint_returns_projected_bar() -> None:
    entity = _anime_entity(
        provider_slug="mal",
        namespace_slug="anime",
        external_id="5000",
    )
    source = CatalogSourceSpec(
        slug="mal",
        name="MyAnimeList",
        base_url="https://myanimelist.net",
    )
    schedule_namespace = SourceNamespaceSpec(
        source=source,
        slug="schedule",
        resource_type=ProviderNamespace.ResourceType.SCHEDULE,
    )
    recorded = source_record_service.record(
        namespace_spec=schedule_namespace,
        fetched=FetchedSourceRecord(
            external_id="weekly:monday",
            payload={
                "weekday": "monday",
                "pages": [
                    {
                        "data": [
                            {
                                "mal_id": 5000,
                                "status": "Currently Airing",
                                "broadcast": {
                                    "day": "Mondays",
                                    "time": "22:00",
                                    "timezone": "Asia/Tokyo",
                                },
                            }
                        ]
                    }
                ],
            },
            schema_version="jikan-v4",
        ),
    )
    knowledge_ingestion_service.record_observation(
        provider_record=recorded.record,
        mapper="mal.weekly",
        mapper_version="mal-schedule-v1",
        normalized_data={
            "weekday": "monday",
            "pages": [
                {
                    "data": [
                        {
                            "mal_id": 5000,
                            "status": "Currently Airing",
                            "broadcast": {
                                "day": "Mondays",
                                "time": "22:00",
                                "timezone": "Asia/Tokyo",
                            },
                        }
                    ]
                }
            ],
        },
        schema_name="index.schedule",
        schema_version="1",
    )
    airing_board_projection_service.rebuild()

    response = APIClient().get("/api/v1/index/calendar/board/events/?include_work=true")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["work_id"] == str(entity.id)
    assert payload[0]["precision"] == "minute"
    assert payload[0]["work"]["id"] == str(entity.id)
