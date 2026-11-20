from unittest.mock import AsyncMock, Mock

import pytest

from api.integrations.providers.errors import ProviderError
from api.worker import bangumi_sync, campaign_imports
from api.worker.tasks import campaigns as campaign_tasks


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,factory,method,external",
    [
        ("vndb", "VNDBClient", "fetch_import_batch", "v1"),
        ("anilist", "AniListClient", "fetch_media", "1"),
        ("mal", "MALClient", "fetch_anime", "1"),
        ("bangumi", "BangumiClient", None, "1"),
    ],
)
async def test_campaign_fetch_delegates_policy_and_closes_transport(
    provider,
    factory,
    method,
    external,
    monkeypatch,
):
    client = Mock()
    monkeypatch.setattr(campaign_imports, factory, Mock(return_value=client))
    if method is None:
        fetch = AsyncMock(side_effect=ProviderError("provider unavailable"))
        monkeypatch.setattr(bangumi_sync, "fetch_batch", fetch)
    else:
        getattr(client, method).side_effect = ProviderError("provider unavailable")
    with pytest.raises(ProviderError):
        await campaign_imports.fetch_source(
            provider, external, forbidden=True, progress=AsyncMock()
        )
    client.forbid_storage.assert_called_once_with(forbidden=True)
    client.close.assert_called_once()


def test_campaign_task_schedules_the_next_durable_step_with_request_identity(monkeypatch):
    outcome = campaign_tasks.StepResult({"campaign_id": "campaign", "status": "fetching"}, 17)
    execute = AsyncMock(return_value=outcome)
    monkeypatch.setattr(campaign_tasks, "execute", execute)
    publisher = Mock()
    monkeypatch.setattr(campaign_tasks.run_sync_campaign_task, "apply_async", publisher)
    execution = campaign_tasks.run_sync_campaign_task.apply(
        args=["campaign"], kwargs={"max_items": 3}
    )
    assert execution.get() == outcome.result
    execute.assert_awaited_once_with("campaign", max_items=3, owner=f"celery:{execution.id}")
    publisher.assert_called_once_with(args=["campaign"], kwargs={"max_items": 3}, countdown=17)


def test_continuation_publish_failure_is_recorded_and_retried(monkeypatch):
    from celery.exceptions import Retry

    outcome = campaign_tasks.StepResult({"campaign_id": "campaign", "status": "fetching"}, 1)
    execute = AsyncMock(return_value=outcome)
    failed = AsyncMock()
    publisher = Mock(side_effect=RuntimeError("broker unavailable"))
    monkeypatch.setattr(campaign_tasks, "execute", execute)
    monkeypatch.setattr(campaign_tasks, "record_publish_failure", failed)
    monkeypatch.setattr(campaign_tasks.run_sync_campaign_task, "apply_async", publisher)
    with pytest.raises(Retry):
        campaign_tasks.run_sync_campaign_task.apply(args=["campaign"], throw=True)
    assert execute.await_count == 1
    failed.assert_awaited_once()
