from unittest.mock import Mock, patch

import pytest

from apps.sync.models import SyncCampaign
from apps.sync.tasks.vndb import run_vndb_incremental_task


@pytest.mark.django_db
def test_the_daily_vndb_task_creates_one_incremental_campaign_a_day() -> None:
    """VNDB has no schedule otherwise, so this task is what keeps it current."""
    with patch(
        "apps.sync.tasks.vndb.run_sync_campaign_task.delay",
        return_value=Mock(id="task-1"),
    ) as delay:
        result = run_vndb_incremental_task()

    campaign = SyncCampaign.objects.get(pk=result["campaign_id"])
    assert campaign.provider_slug == "vndb"
    assert campaign.campaign_type == "incremental"
    assert campaign.idempotency_key.startswith("vndb-incremental-")
    delay.assert_called_once_with(str(campaign.pk))


@pytest.mark.django_db
def test_running_it_twice_in_a_day_does_not_queue_a_second_sweep() -> None:
    with patch(
        "apps.sync.tasks.vndb.run_sync_campaign_task.delay", return_value=Mock(id="t")
    ):
        first = run_vndb_incremental_task()
        second = run_vndb_incremental_task()

    assert first["campaign_id"] == second["campaign_id"]
    assert SyncCampaign.objects.count() == 1
