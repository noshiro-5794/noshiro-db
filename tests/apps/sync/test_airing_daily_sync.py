from unittest.mock import patch

import pytest

from apps.index.models import (
    AiringEvent,
    Entity,
    Observation,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services.airing_board import airing_board_service
from apps.sync.models import SyncState
from apps.sync.services.airing_daily_sync_service import airing_daily_sync_service

pytestmark = pytest.mark.django_db(transaction=True)


def _calendar_board(*ids: int) -> Observation:
    provider, _ = Provider.objects.get_or_create(
        slug="bangumi",
        defaults={"name": "Bangumi", "storage_policy": "allowed"},
    )
    subject_ns, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="subject",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    calendar_ns, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="calendar",
        defaults={"resource_type": ProviderNamespace.ResourceType.SCHEDULE},
    )
    observation = Observation.objects.create(
        provider_record=ProviderRecord.objects.create(
            namespace=calendar_ns,
            external_id="weekly",
            origin=ProviderRecord.Origin.API,
            status=ProviderRecord.Status.ACTIVE,
        ),
        origin=Observation.Origin.LEGACY,
        schema_name="index.schedule",
        schema_version="1",
        normalized_data={"groups": []},
        normalized_hash="calendar-hash",
    )
    for index, external_id in enumerate(ids, start=1):
        record = ProviderRecord.objects.create(
            namespace=subject_ns,
            external_id=str(external_id),
            origin=ProviderRecord.Origin.API,
            status=ProviderRecord.Status.ACTIVE,
        )
        entity = Entity.objects.create(kind=Entity.Kind.WORK)
        Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
        ProviderRepresentation.objects.create(
            provider_record=record,
            entity=entity,
            mapping_kind=ProviderRepresentation.MappingKind.EXACT,
            method=ProviderRepresentation.Method.EXTERNAL_ID,
        )
        AiringEvent.objects.create(
            work_id=entity.id,
            weekday=index,
            precision=AiringEvent.Precision.WEEKDAY,
            raw_value="Weekday",
            observation=observation,
        )
    airing_board_service.refresh(
        observation=observation,
        season_key="2026Q3",
        item_count=len(ids),
    )
    return observation


def test_daily_refresh_processes_board_in_bounded_batches() -> None:
    _calendar_board(101, 102)
    calls: list[int] = []

    def _upsert(bangumi_id: int):
        calls.append(bangumi_id)
        return Entity.objects.first()

    with (
        patch(
            "apps.sync.services.airing_daily_sync_service.subject_service.upsert_subject",
            side_effect=_upsert,
        ),
        patch(
            "apps.sync.services.airing_daily_sync_service.episode_service.sync_subject_episodes"
        ) as episodes,
    ):
        first = airing_daily_sync_service.sync_day(batch_size=1)
        second = airing_daily_sync_service.sync_day(batch_size=1)
        third = airing_daily_sync_service.sync_day(batch_size=1)

    assert calls == [101, 102]
    assert episodes.call_count == 2
    assert first["processed_count"] == 1
    assert first["completed"] is False
    assert second["processed_count"] == 1
    assert second["completed"] is True
    assert third["processed_count"] == 0
    assert third["completed"] is True
    state = SyncState.objects.get(
        task_name=airing_daily_sync_service.TASK_NAME,
        shard=first["shard"],
    )
    assert state.status == SyncState.Status.FINISHED
    assert state.current_id == 2


def test_daily_status_reports_current_shard() -> None:
    _calendar_board(101)
    status = airing_daily_sync_service.get_status(season_key="2026Q3")
    assert status["state"] is None

    airing_daily_sync_service.sync_day(batch_size=1)
    status = airing_daily_sync_service.get_status(season_key="2026Q3")
    assert status["state"] is not None
    assert status["state"]["status"] == SyncState.Status.FINISHED
