from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from api.db import fetch
from api.integrations.providers.bangumi import BangumiClient
from api.integrations.providers.errors import ProviderError
from api.worker import bangumi_sync, jobs
from api.worker.tasks import manual_sync
from tests.ingestion.test_bangumi_graph_transactions import (
    CHARACTER_DETAILS,
    CHARACTERS,
    EPISODES,
    PEOPLE,
    STAFF,
    SUBJECT,
    SUBJECTS,
)


@pytest.fixture
async def manual_runtime(bangumi_session, monkeypatch):
    session = bangumi_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    responses = {
        "/v0/subjects/1": SUBJECT,
        "/v0/episodes": {"data": EPISODES},
        "/v0/subjects/1/subjects": SUBJECTS,
        "/v0/subjects/1/persons": STAFF,
        "/v0/subjects/1/characters": CHARACTERS,
        "/v0/persons/20": PEOPLE["20"],
        "/v0/persons/21": PEOPLE["21"],
        "/v0/characters/30": CHARACTER_DETAILS["30"],
    }
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=responses[request.url.path])

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://provider.test")
    client = BangumiClient(http=http)
    monkeypatch.setattr(manual_sync, "session_scope", scope)
    monkeypatch.setattr(manual_sync, "BangumiClient", Mock(return_value=client))
    job_id = str(await jobs.create_job(session, job_type="sync_subject"))
    await session.commit()
    return session, job_id, http, requests, responses


@pytest.mark.asyncio
async def test_manual_sync_entry_fetches_full_graph_and_finishes_once(manual_runtime):
    session, job_id, http, requests, _ = manual_runtime
    result = await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker")
    assert result["staff_count"] == 2
    assert result["character_count"] == 1
    assert len(requests) == 8
    assert http.is_closed
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.total_count, row.processed_count, row.synced_count) == (
        "succeeded",
        6,
        6,
        6,
    )
    assert await manual_sync.subject_identifier(session, result["subject_id"]) == 1
    assert await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker") == {
        "skipped": True,
        "reason": "job already claimed",
    }
    assert len(requests) == 8


@pytest.mark.asyncio
async def test_storage_policy_fails_job_before_any_request(manual_runtime):
    session, job_id, http, requests, _ = manual_runtime
    await fetch(
        session,
        "UPDATE provider SET storage_policy='forbidden' WHERE slug='bangumi' RETURNING id",
        {},
    )
    await session.commit()
    with pytest.raises(ProviderError, match="forbids"):
        await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker")
    assert not requests
    assert http.is_closed
    row = (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert row.status == "failed"


@pytest.mark.asyncio
async def test_late_provider_failure_preserves_empty_catalogue(manual_runtime):
    session, job_id, http, _, responses = manual_runtime
    responses["/v0/persons/21"] = {"id": 999}
    with pytest.raises(ProviderError, match="inconsistent"):
        await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker")
    assert http.is_closed
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ].status == "failed"


@pytest.mark.asyncio
async def test_cancelled_job_cannot_project_fetched_graph(manual_runtime, monkeypatch):
    session, job_id, _, _, _ = manual_runtime
    original = bangumi_sync.fetch_batch

    async def cancel_after_fetch(*args, **kwargs):
        batch = await original(*args, **kwargs)
        await fetch(
            session,
            "UPDATE sync_job SET status='cancelled' WHERE id=:id RETURNING id",
            {"id": job_id},
        )
        await session.commit()
        return batch

    monkeypatch.setattr(bangumi_sync, "fetch_batch", cancel_after_fetch)
    with pytest.raises(manual_sync.JobLeaseLost):
        await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker")
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ].status == "cancelled"


@pytest.mark.asyncio
async def test_projection_failure_rolls_back_graph_and_records_failure(manual_runtime, monkeypatch):
    session, job_id, _, _, _ = manual_runtime
    monkeypatch.setattr(
        bangumi_sync, "import_entity", AsyncMock(side_effect=ValueError("invalid character"))
    )
    with pytest.raises(ValueError, match="invalid character"):
        await manual_sync.synchronize(bangumi_id=1, job_id=job_id, lease_owner="worker")
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    row = (await fetch(session, "SELECT status,error FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ]
    assert (row.status, row.error) == ("failed", "invalid character")
