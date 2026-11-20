from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.integrations.providers.vndb import VNDBImportBatch
from api.worker import importing, jobs
from api.worker.tasks import vndb as vndb_tasks


@pytest.fixture
async def task_runtime(vndb_session, monkeypatch):
    session = vndb_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(importing, "session_scope", scope)
    client = Mock()
    client.fetch_import_batch.return_value = VNDBImportBatch(work={"id": "v1", "title": "VN"})
    monkeypatch.setattr(vndb_tasks, "VNDBClient", Mock(return_value=client))
    identifier = await jobs.create_job(session, job_type="import_vndb")
    await session.commit()
    return session, str(identifier), client


@pytest.mark.asyncio
async def test_task_entry_claims_job_imports_and_finishes_once(task_runtime):
    session, job_id, client = task_runtime
    result = await vndb_tasks.import_work(
        "v1", include_related=False, job_id=job_id, lease_owner="worker"
    )
    assert result["provider"] == "vndb"
    assert result["external_id"] == "v1"
    client.fetch_import_batch.assert_called_once_with("v1", include_related=False)
    client.close.assert_called_once()
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.processed_count, row.synced_count) == ("succeeded", 1, 1)
    assert await vndb_tasks.import_work(
        "v1", include_related=True, job_id=job_id, lease_owner="worker"
    ) == {"skipped": True, "reason": "job already claimed"}
    client.fetch_import_batch.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_failure_is_committed_and_transport_is_closed(task_runtime):
    session, job_id, client = task_runtime
    client.fetch_import_batch.side_effect = ProviderError(
        "temporarily unavailable", status_code=503
    )
    with pytest.raises(ProviderError):
        await vndb_tasks.import_work(
            "v1", include_related=True, job_id=job_id, lease_owner="worker"
        )
    client.close.assert_called_once()
    row = (await fetch(session, "SELECT status, error FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ]
    assert (row.status, row.error) == ("failed", "temporarily unavailable")
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_projection_failure_rolls_back_data_and_commits_failure(task_runtime, monkeypatch):
    session, job_id, _ = task_runtime
    monkeypatch.setattr(
        vndb_tasks, "import_batch", AsyncMock(side_effect=ValueError("bad projection"))
    )
    with pytest.raises(ValueError, match="bad projection"):
        await vndb_tasks.import_work(
            "v1", include_related=True, job_id=job_id, lease_owner="worker"
        )
    row = (await fetch(session, "SELECT status, error FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ]
    assert (row.status, row.error) == ("failed", "bad projection")


@pytest.mark.asyncio
async def test_job_cancelled_during_fetch_cannot_write_catalogue(task_runtime, monkeypatch):
    session, job_id, client = task_runtime

    async def cancel_during_fetch(*args, **kwargs):
        await fetch(
            session,
            "UPDATE sync_job SET status='cancelled' WHERE id=:id RETURNING id",
            {"id": job_id},
        )
        await session.commit()
        return client.fetch_import_batch.return_value

    monkeypatch.setattr(vndb_tasks.asyncio, "to_thread", cancel_during_fetch)
    assert await vndb_tasks.import_work(
        "v1", include_related=True, job_id=job_id, lease_owner="worker"
    ) == {"skipped": True, "reason": "job lease lost"}
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
