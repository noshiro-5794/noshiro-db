from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.sync.models import SyncError

pytestmark = pytest.mark.django_db


def _error(task_name: str, entity_id: int, *, days_ago: int) -> SyncError:
    entry = SyncError.objects.create(
        task_name=task_name,
        entity_id=entity_id,
        retry_count=1,
    )
    # auto_now ignores values passed to create(), so age the row afterwards.
    SyncError.objects.filter(pk=entry.pk).update(
        first_occurred_at=timezone.now() - timedelta(days=days_ago),
        last_occurred_at=timezone.now() - timedelta(days=days_ago),
    )
    entry.refresh_from_db()
    return entry


class TestRetrySyncErrors:
    def test_retries_reachable_entities_and_prunes_stale_ones(self) -> None:
        stale = _error("full_subject", 1, days_ago=120)
        retryable = _error("incremental_subject", 2, days_ago=1)
        unretryable = _error("calendar", 3, days_ago=1)

        with patch(
            "apps.sync.services.incremental_sync_service."
            "IncrementalSyncService._sync_one",
            return_value="synced",
        ) as sync_one:
            call_command(
                "retry_sync_errors",
                "--stale-before",
                (timezone.now() - timedelta(days=30)).date().isoformat(),
                stdout=StringIO(),
            )

        sync_one.assert_called_once()
        assert not SyncError.objects.filter(pk=stale.pk).exists()
        assert not SyncError.objects.filter(pk=retryable.pk).exists()
        assert SyncError.objects.filter(pk=unretryable.pk).exists()

    def test_keeps_the_entry_and_counts_the_retry_when_a_fetch_fails(self) -> None:
        entry = _error("incremental_subject", 4, days_ago=1)

        with patch(
            "apps.sync.services.incremental_sync_service."
            "IncrementalSyncService._sync_one",
            return_value="failed",
        ):
            call_command("retry_sync_errors", stdout=StringIO())

        entry.refresh_from_db()
        assert entry.retry_count == 2

    def test_dry_run_changes_nothing(self) -> None:
        entry = _error("incremental_subject", 5, days_ago=1)

        with patch(
            "apps.sync.services.incremental_sync_service."
            "IncrementalSyncService._sync_one",
        ) as sync_one:
            call_command(
                "retry_sync_errors",
                "--stale-before",
                timezone.now().date().isoformat(),
                "--dry-run",
                stdout=StringIO(),
            )

        sync_one.assert_not_called()
        assert SyncError.objects.filter(pk=entry.pk).exists()
