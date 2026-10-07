from unittest.mock import patch

import pytest

from apps.index.models import (
    Entity,
    IndexCollection,
    IndexMembership,
    Provider,
    ProviderNamespace,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.sync.models import SyncError
from apps.sync.providers.exceptions import BangumiAPIError
from apps.sync.services.subject_refresh_service import subject_refresh_service

pytestmark = pytest.mark.django_db


def _subject_record(
    external_id: str,
    *,
    raw_state: str,
    listed: bool = True,
    last_seen_at=None,
) -> ProviderRecord:
    provider, _ = Provider.objects.get_or_create(
        slug="bangumi", defaults={"name": "Bangumi"}
    )
    namespace, _ = ProviderNamespace.objects.get_or_create(
        provider=provider,
        slug="subject",
        defaults={"resource_type": ProviderNamespace.ResourceType.SUBJECT},
    )
    record = ProviderRecord.objects.create(
        namespace=namespace,
        external_id=external_id,
        origin="api",
        status=ProviderRecord.Status.ACTIVE,
        raw_state=raw_state,
    )
    if last_seen_at is not None:
        ProviderRecord.objects.filter(pk=record.pk).update(last_seen_at=last_seen_at)
    if listed:
        entity = Entity.objects.create(kind=Entity.Kind.WORK)
        Work.objects.create(entity=entity, work_type=Work.WorkType.ANIME)
        collection, _ = IndexCollection.objects.get_or_create(
            slug="anime", defaults={"name": "Anime"}
        )
        IndexMembership.objects.create(
            collection=collection,
            entity=entity,
            listing_state=IndexMembership.State.LISTED,
        )
        ProviderRepresentation.objects.create(
            entity=entity,
            provider_record=record,
            mapping_kind=ProviderRepresentation.MappingKind.EXACT,
            method=ProviderRepresentation.Method.PROVIDER,
        )
    return record


def test_legacy_catalogue_records_are_selected_first() -> None:
    legacy = _subject_record("100", raw_state=ProviderRecord.RawState.LEGACY)
    fresh = _subject_record("200", raw_state=ProviderRecord.RawState.RAW)
    unlisted = _subject_record(
        "300", raw_state=ProviderRecord.RawState.LEGACY, listed=False
    )

    targets = subject_refresh_service.select_targets(limit=10)

    ids = [record.external_id for record in targets]
    assert ids == [legacy.external_id, fresh.external_id]
    assert unlisted.external_id not in ids

    everything = subject_refresh_service.select_targets(limit=10, catalogue_only=False)
    assert unlisted.external_id in [record.external_id for record in everything]


def test_refresh_promotes_legacy_rows_and_reports_counts() -> None:
    _subject_record("100", raw_state=ProviderRecord.RawState.LEGACY)
    _subject_record("200", raw_state=ProviderRecord.RawState.RAW)

    with patch(
        "apps.sync.services.subject_refresh_service.subject_service.upsert_subject"
    ) as upsert:
        result = subject_refresh_service.refresh(limit=10)

    assert upsert.call_count == 2
    assert result["refreshed"] == 2
    assert result["promoted"] == 1
    assert result["legacy_selected"] == 1
    assert result["failed"] == 0


def test_a_missing_subject_is_retired_not_retried() -> None:
    record = _subject_record("100", raw_state=ProviderRecord.RawState.LEGACY)

    with patch(
        "apps.sync.services.subject_refresh_service.subject_service.upsert_subject",
        side_effect=BangumiAPIError("gone", status_code=404),
    ):
        result = subject_refresh_service.refresh(limit=10)

    record.refresh_from_db()
    assert record.status == ProviderRecord.Status.MISSING
    assert result["missing"] == 1
    assert result["failed"] == 0
    assert SyncError.objects.count() == 0


def test_a_provider_failure_lands_in_the_error_ledger() -> None:
    _subject_record("100", raw_state=ProviderRecord.RawState.LEGACY)

    with patch(
        "apps.sync.services.subject_refresh_service.subject_service.upsert_subject",
        side_effect=BangumiAPIError("boom", status_code=503),
    ):
        result = subject_refresh_service.refresh(limit=10)

    assert result["failed"] == 1
    assert SyncError.objects.filter(task_name="bangumi_subject_refresh").exists()


def test_limit_bounds_the_selection() -> None:
    for index in range(3):
        _subject_record(str(100 + index), raw_state=ProviderRecord.RawState.LEGACY)

    targets = subject_refresh_service.select_targets(limit=2)

    assert len(targets) == 2
