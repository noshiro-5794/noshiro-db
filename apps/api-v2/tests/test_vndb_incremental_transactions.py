from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaigns
from api.shared import dispatch
from api.worker import jobs, vndb_tasks


@pytest.fixture
async def launcher(vndb_session, monkeypatch):
    session = vndb_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(vndb_tasks, "session_scope", scope)
    sender = AsyncMock(return_value="campaign-task")
    monkeypatch.setattr(dispatch, "enqueue", sender)
    job_id = await jobs.create_job(session, job_type="vndb_incremental")
    await session.commit()
    return session, job_id, sender


@pytest.mark.asyncio
async def test_daily_campaign_is_committed_before_dispatch_and_reused(launcher):
    session, job_id, sender = launcher

    async def sent(task, arguments):
        campaign = await campaigns.get_campaign(session, arguments["campaign_id"])
        assert campaign.campaign_type == "incremental"
        assert campaign.parameters == {"fetch_batch_size": 50, "step_delay_seconds": 1}
        assert task == dispatch.SYNC_TASK
        return "campaign-task"

    sender.side_effect = sent
    result = await vndb_tasks.start_incremental(str(job_id), "worker")
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert row.status == "succeeded"
    assert row.result == result
    again = await vndb_tasks.start_incremental(None, "daily-replay")
    assert again["campaign_id"] == result["campaign_id"]
    assert (await fetch(session, "SELECT count(*) AS n FROM sync_campaign", {}))[0].n == 1
    replay = await vndb_tasks.start_incremental(str(job_id), "job-replay")
    assert replay == {"skipped": True, "reason": "job already claimed"}
    assert sender.await_count == 2


@pytest.mark.asyncio
async def test_dispatch_failure_retains_campaign_and_fails_job_for_operator_retry(launcher):
    session, job_id, sender = launcher
    sender.side_effect = dispatch.DispatchUnavailable("Broker unavailable")
    with pytest.raises(dispatch.DispatchUnavailable):
        await vndb_tasks.start_incremental(str(job_id), "worker")
    row = (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert row.status == "failed"
    campaign = (await fetch(session, "SELECT id,status FROM sync_campaign", {}))[0]
    assert campaign.status == "queued"
    sender.side_effect = None
    result = await vndb_tasks.start_incremental(None, "retry")
    assert result["campaign_id"] == str(campaign.id)
