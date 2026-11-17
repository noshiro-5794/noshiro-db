from unittest.mock import AsyncMock

import httpx
import pytest

from api.worker import bangumi_sync, manual_sync
from api.worker.providers.bangumi import BangumiClient


@pytest.mark.parametrize(
    ("task", "arguments"),
    [
        (manual_sync.sync_subject_by_uuid_task, {"subject_id": "subject"}),
        (manual_sync.sync_subject_by_bangumi_id_task, {"bangumi_id": 1}),
    ],
)
def test_registered_tasks_preserve_arguments_and_request_identity(monkeypatch, task, arguments):
    synchronize = AsyncMock(return_value={"subject_id": "subject"})
    monkeypatch.setattr(manual_sync, "synchronize", synchronize)
    result = task.apply(kwargs={**arguments, "job_id": "job"})
    assert result.get() == {"subject_id": "subject"}
    synchronize.assert_awaited_once_with(
        **arguments, job_id="job", lease_owner=f"celery:{result.id}"
    )


@pytest.mark.asyncio
async def test_complete_fetch_paginates_episodes_and_deduplicates_person_details():
    requests = []

    def handler(request):
        path = request.url.path
        requests.append(str(request.url))
        if path == "/v0/subjects/1":
            data = {"id": 1}
        elif path == "/v0/episodes":
            assert request.url.params["subject_id"] == "1"
            assert request.url.params["limit"] == "100"
            offset = int(request.url.params["offset"])
            data = {"data": [{"id": i} for i in range(100)] if offset == 0 else []}
        elif path.endswith("/persons"):
            data = [{"id": 20}]
        elif path.endswith("/characters"):
            data = [{"id": 30, "actors": [{"id": 20}, {"id": 20}]}]
        elif path.endswith("/subjects"):
            data = []
        else:
            data = {"id": int(path.rsplit("/", 1)[1])}
        return httpx.Response(200, json=data)

    client = BangumiClient(transport=httpx.MockTransport(handler))
    progress = AsyncMock()
    try:
        batch = await bangumi_sync.fetch_batch(client, 1, progress=progress)
    finally:
        client.close()
    assert len(batch.episodes) == 100
    assert len(batch.people_details) == 1
    assert sum("/v0/persons/20" in url for url in requests) == 1
    assert any("offset=100" in url for url in requests)
    progress.assert_awaited_with("Fetched staff 20", 5)
