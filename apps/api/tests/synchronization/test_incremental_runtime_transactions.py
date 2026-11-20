from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.worker import jobs
from api.worker.subject_import import import_subject
from api.worker.tasks import incremental as incremental_tasks


@pytest.fixture
async def incremental_runtime(bangumi_session, monkeypatch):
    session = bangumi_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(incremental_tasks, "session_scope", scope)
    client = Mock()
    client.fetch_subject.side_effect = lambda identifier: {
        "id": identifier,
        "type": 2,
        "name": f"Anime {identifier}",
    }
    client.fetch_subject_subjects.return_value = []
    client.fetch_subject_persons.return_value = []
    client.fetch_subject_characters.return_value = []
    client.fetch_subject_episodes.return_value = {"data": []}
    client.fetch_character.side_effect = lambda identifier: {"id": identifier, "name": "Character"}
    client.fetch_person.side_effect = lambda identifier: {
        "id": identifier,
        "name": "Person",
        "type": 1,
    }
    monkeypatch.setattr(incremental_tasks, "BangumiClient", lambda: client)
    return session, client


@pytest.mark.asyncio
async def test_subject_window_commits_imports_and_cursor_then_continues(incremental_runtime):
    session, client = incremental_runtime
    result = await incremental_tasks.execute(
        task_name="incremental_subject", batch_size=2, job_id=None, owner="worker"
    )
    assert result["start_id"] == 1 and result["end_id"] == 2 and result["synced_count"] == 2
    state = (await fetch(session, "SELECT * FROM sync_state", {}))[0]
    assert state.current_id == 2 and state.status == "finished"
    again = await incremental_tasks.execute(
        task_name="incremental_subject", batch_size=1, job_id=None, owner="next"
    )
    assert again["start_id"] == 3 and again["synced_count"] == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 3
    assert client.close.call_count == 2


@pytest.mark.asyncio
async def test_all_windows_preserve_job_totals_and_duplicate_delivery(incremental_runtime):
    session, client = incremental_runtime
    job_id = await jobs.create_job(session, job_type="incremental")
    await session.commit()
    result = await incremental_tasks.execute(
        task_name=None, batch_size=1, job_id=str(job_id), owner="worker"
    )
    assert len(result["results"]) == 8
    job = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert job.status == "succeeded"
    assert job.total_count == job.processed_count == 8
    replay = await incremental_tasks.execute(
        task_name=None, batch_size=1, job_id=str(job_id), owner="replay"
    )
    assert replay == {"skipped": True, "reason": "job already claimed"}
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_frontier_preserves_last_live_identifier(incremental_runtime, monkeypatch):
    session, client = incremental_runtime
    monkeypatch.setenv("SYNC_INCREMENTAL_MAX_CONSECUTIVE_SKIPS", "2")
    client.fetch_subject.side_effect = [
        {"id": 1, "type": 2, "name": "Anime"},
        ProviderError("Missing", status_code=404),
        ProviderError("Missing", status_code=404),
    ]
    result = await incremental_tasks.execute(
        task_name="incremental_subject", batch_size=10, job_id=None, owner="worker"
    )
    assert result["frontier_reached"] is True
    assert result["processed_count"] == 3 and result["skipped_count"] == 2
    assert (await fetch(session, "SELECT current_id FROM sync_state", {}))[0].current_id == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM sync_error", {}))[0].n == 0


@pytest.mark.asyncio
async def test_repeated_errors_persist_failure_ledger_and_job_failure(
    incremental_runtime, monkeypatch
):
    session, client = incremental_runtime
    monkeypatch.setenv("SYNC_INCREMENTAL_MAX_CONSECUTIVE_ERRORS", "2")
    client.fetch_subject.side_effect = ProviderError("Unavailable", status_code=503)
    job_id = await jobs.create_job(session, job_type="incremental")
    await session.commit()
    with pytest.raises(RuntimeError, match="Too many consecutive"):
        await incremental_tasks.execute(
            task_name="incremental_subject", batch_size=4, job_id=str(job_id), owner="worker"
        )
    state = (await fetch(session, "SELECT * FROM sync_state", {}))[0]
    assert state.status == "failed" and state.fail_count == 1 and state.current_id == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM sync_error", {}))[0].n == 2
    assert (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ].status == "failed"


@pytest.mark.asyncio
async def test_state_replacement_during_fetch_prevents_late_projection(incremental_runtime):
    session, _client = incremental_runtime

    def replaced(identifier):
        return {"id": identifier, "type": 2, "name": "Late"}

    real_fetch = incremental_tasks.fetch_source

    async def changed(*args):
        await fetch(
            session,
            "UPDATE sync_state SET status='running',updated_at=clock_timestamp() RETURNING id",
            {},
        )
        await session.commit()
        return replaced(1)

    import asyncio

    original = asyncio.to_thread

    async def threaded(function, *args, **kwargs):
        if function is real_fetch:
            return await changed(*args)
        return await original(function, *args, **kwargs)

    from unittest.mock import patch

    from api.contexts.synchronization.domain import LeaseLost

    with patch.object(incremental_tasks.asyncio, "to_thread", threaded), pytest.raises(LeaseLost):
        await incremental_tasks.execute(
            task_name="incremental_subject", batch_size=1, job_id=None, owner="worker"
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM sync_state", {}))[0].status == "running"


@pytest.mark.asyncio
async def test_relation_window_keeps_other_collection_observations(incremental_runtime):
    session, client = incremental_runtime
    await import_subject(session, {"id": 1, "type": 2, "name": "Anime"})
    await fetch(
        session,
        "INSERT INTO sync_state(task_name,shard,current_id,end_id,status,fail_count,updated_at) "
        "VALUES ('incremental_subject_staff_relation','main',0,0,'idle',0,now()) RETURNING id",
        {},
    )
    client.fetch_subject_persons.return_value = [
        {"id": 3, "relation": "Director", "name": "Person"}
    ]
    await session.commit()
    result = await incremental_tasks.execute(
        task_name="incremental_subject_staff_relation", batch_size=1, job_id=None, owner="worker"
    )
    assert result["synced_count"] == 1
    namespaces = await fetch(session, "SELECT slug FROM provider_namespace ORDER BY slug", {})
    assert [row.slug for row in namespaces] == ["person", "subject", "subject-staff"]
    client.fetch_subject_subjects.assert_not_called()
    client.fetch_subject_characters.assert_not_called()
    assert (await fetch(session, "SELECT count(*) AS n FROM credit", {}))[0].n == 1


@pytest.mark.asyncio
async def test_projection_failure_rolls_back_partial_source_and_records_item_error(
    incremental_runtime, monkeypatch
):
    session, _ = incremental_runtime

    async def broken(session, part, identifier, payload):
        await import_subject(session, payload)
        raise ValueError("Projection failed")

    monkeypatch.setattr(incremental_tasks, "project", broken)
    result = await incremental_tasks.execute(
        task_name="incremental_subject", batch_size=1, job_id=None, owner="worker"
    )
    assert result["failed_count"] == 1 and result["synced_count"] == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM sync_error", {}))[0].n == 1


@pytest.mark.asyncio
async def test_live_window_cannot_be_claimed_again(incremental_runtime):
    from api.contexts.synchronization import incremental

    session, client = incremental_runtime
    config = incremental.CONFIGS["incremental_subject"]
    await incremental.start_window(session, config, 2)
    await session.commit()
    with pytest.raises(incremental.AlreadyRunning):
        await incremental_tasks.execute(
            task_name=config.name, batch_size=1, job_id=None, owner="duplicate"
        )
    assert (await fetch(session, "SELECT status FROM sync_state", {}))[0].status == "running"
    client.fetch_subject.assert_not_called()
    client.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,namespace",
    [
        ("incremental_episode", "subject-episodes"),
        ("incremental_subject_subject_relation", "subject-relations"),
        ("incremental_subject_character_relation", "subject-characters"),
        ("incremental_character", "character"),
        ("incremental_staff", "person"),
    ],
)
async def test_each_incremental_projection_uses_existing_importers(
    incremental_runtime, name, namespace
):
    session, client = incremental_runtime
    await import_subject(session, {"id": 1, "type": 2, "name": "Anime"})
    await fetch(
        session,
        "INSERT INTO sync_state(task_name,shard,current_id,end_id,status,fail_count,updated_at) "
        "VALUES (:name,'main',0,0,'idle',0,now()) RETURNING id",
        {"name": name},
    )
    await session.commit()
    client.fetch_subject_episodes.return_value = {
        "data": [{"id": 11, "ep": 1, "type": 0, "name": "Episode"}]
    }
    client.fetch_subject_subjects.return_value = [{"id": 2, "relation": "续集"}]
    client.fetch_subject_characters.return_value = [
        {"id": 3, "relation": "主角", "actors": [{"id": 4, "name": "Actor"}]}
    ]
    result = await incremental_tasks.execute(
        task_name=name, batch_size=1, job_id=None, owner="worker"
    )
    assert result["synced_count"] == 1
    assert await fetch(
        session, "SELECT 1 FROM provider_namespace WHERE slug=:namespace", {"namespace": namespace}
    )


@pytest.mark.asyncio
async def test_running_window_is_preserved_and_legacy_finished_cursor_initializes_next_pass(
    incremental_runtime,
):
    from api.contexts.synchronization import incremental

    session, client = incremental_runtime
    await fetch(
        session,
        "INSERT INTO sync_state(task_name,shard,current_id,end_id,status,fail_count,updated_at) "
        "VALUES ('full_subject','chunk',0,42,'finished',0,now()) RETURNING id",
        {},
    )
    await session.commit()
    result = await incremental_tasks.execute(
        task_name="incremental_subject", batch_size=1, job_id=None, owner="worker"
    )
    assert result["start_id"] == 43
    await fetch(
        session,
        "UPDATE sync_state SET status='running',updated_at=clock_timestamp() "
        "WHERE task_name='incremental_subject' RETURNING id",
        {},
    )
    await session.commit()
    with pytest.raises(incremental.AlreadyRunning):
        await incremental_tasks.execute(
            task_name="incremental_subject", batch_size=1, job_id=None, owner="duplicate"
        )
    assert (
        await fetch(
            session, "SELECT status FROM sync_state WHERE task_name='incremental_subject'", {}
        )
    )[0].status == "running"
    assert client.fetch_subject.call_count == 1


@pytest.mark.asyncio
async def test_stale_scanner_rechecks_timestamp_before_unlocking(incremental_runtime, monkeypatch):
    from api.worker.tasks import maintenance as tasks

    session, _ = incremental_runtime
    await fetch(
        session,
        "INSERT INTO sync_state(task_name,shard,current_id,end_id,status,fail_count,updated_at) "
        "VALUES ('incremental_subject','main',0,0,'running',0,now()-interval '2 hours') "
        "RETURNING id",
        {},
    )
    await session.commit()
    monkeypatch.setattr(tasks, "session_scope", incremental_tasks.session_scope)
    real_fetch = tasks.fetch

    async def heartbeat_before_update(session, query, parameters):
        if query.startswith("UPDATE sync_state"):
            await real_fetch(
                session, "UPDATE sync_state SET updated_at=clock_timestamp() RETURNING id", {}
            )
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(tasks, "fetch", heartbeat_before_update)
    result = await tasks._scan_stale_sync_states(60)
    assert result == {"stale_states": 0}
    assert (await fetch(session, "SELECT status,fail_count FROM sync_state", {}))[
        0
    ].status == "running"
