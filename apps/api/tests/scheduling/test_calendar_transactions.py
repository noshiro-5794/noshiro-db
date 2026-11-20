from datetime import UTC, datetime

import pytest

from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.worker import calendar_sync
from api.worker.tasks import calendar as calendar_tasks
from api.worker.tasks import manual_sync
from tests.synchronization.test_bangumi_manual_transactions import manual_runtime as manual_runtime

CALENDAR = [{"weekday": {"id": 1, "en": "Mon"}, "items": [{"id": 1, "collection": {"doing": 12}}]}]


@pytest.fixture
async def calendar_runtime(manual_runtime, monkeypatch):
    session, job_id, http, requests, responses = manual_runtime
    responses["/calendar"] = CALENDAR
    monkeypatch.setattr(calendar_tasks, "session_scope", manual_sync.session_scope)
    monkeypatch.setattr(calendar_tasks, "BangumiClient", manual_sync.BangumiClient)
    return session, job_id, http, requests, responses


@pytest.mark.asyncio
async def test_calendar_task_imports_unknown_base_subject_before_building_events(calendar_runtime):
    session, job_id, http, requests, _ = calendar_runtime
    result = await calendar_tasks.synchronize(
        sync_subject_details=False, job_id=job_id, lease_owner="worker"
    )
    assert result["synced_subject_count"] == 1
    assert result["failed_subject_count"] == 0
    assert result["added_subject_ids"] == [1]
    assert result["detail_synced_count"] == 0
    assert result["board"]["item_count"] == 1
    events = await fetch(session, "SELECT weekday,collection_doing FROM airing_event", {})
    assert [tuple(row) for row in events] == [(1, 12)]
    assert len(requests) == 2
    assert http.is_closed
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.total_count, row.processed_count, row.synced_count) == (
        "succeeded",
        1,
        1,
        1,
    )


@pytest.mark.asyncio
async def test_calendar_can_run_complete_manual_details_and_preserve_parent_job_totals(
    calendar_runtime,
):
    session, job_id, _, requests, _ = calendar_runtime
    result = await calendar_tasks.synchronize(
        sync_subject_details=True, job_id=job_id, lease_owner="worker"
    )
    assert result["detail_synced_count"] == 1
    assert result["detail_failed_count"] == 0
    assert len(requests) == 10
    assert (await fetch(session, "SELECT count(*) AS n FROM voice_performance", {}))[0].n == 1
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.total_count, row.processed_count, row.synced_count) == (
        "succeeded",
        2,
        2,
        1,
    )


@pytest.mark.asyncio
async def test_detail_failure_keeps_refreshed_board_and_records_retry(calendar_runtime):
    session, job_id, http, _, responses = calendar_runtime
    responses["/v0/persons/21"] = {"id": 999}
    result = await calendar_tasks.synchronize(
        sync_subject_details=True, job_id=job_id, lease_owner="worker"
    )
    assert result["detail_failed_count"] == 1
    assert result["detail_synced_count"] == 0
    assert http.is_closed
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_event", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM appearance", {}))[0].n == 0
    assert [
        tuple(row)
        for row in await fetch(
            session, "SELECT task_name,entity_id,retry_count FROM sync_error", {}
        )
    ] == [("calendar", 1, 0)]
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.processed_count, row.failed_count) == ("succeeded", 2, 1)


@pytest.mark.asyncio
async def test_forbidden_provider_commits_failure_without_requesting_calendar(calendar_runtime):
    session, job_id, http, requests, _ = calendar_runtime
    await fetch(
        session,
        "UPDATE provider SET storage_policy='forbidden' WHERE slug='bangumi' RETURNING id",
        {},
    )
    await session.commit()
    with pytest.raises(ProviderError):
        await calendar_tasks.synchronize(
            sync_subject_details=False, job_id=job_id, lease_owner="worker"
        )
    assert not requests
    assert http.is_closed
    assert (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ].status == "failed"


@pytest.mark.asyncio
async def test_same_season_refresh_preserves_curated_board_then_archives_on_rollover(
    bangumi_session,
):
    session = bangumi_session
    from api.worker.subject_import import import_subject

    work_id = await import_subject(session, {"id": 1, "name": "Anime", "type": 2})
    first = await calendar_sync.apply_calendar(
        session, CALENDAR, now=datetime(2026, 1, 1, tzinfo=UTC)
    )
    await fetch(
        session,
        "UPDATE airing_board SET item_count=7,metadata='{}'::jsonb WHERE id=:id RETURNING id",
        {"id": first["board_id"]},
    )
    await fetch(
        session,
        """
        INSERT INTO airing_board_entry
          (id,board_id,work_id,timezone,region,precision,status,decision,confidence,
           source_refs,created_at,updated_at)
        VALUES (gen_random_uuid(),:board,:work,'Asia/Tokyo','','weekday','active','accepted',
                1,'[]'::jsonb,now(),now()) RETURNING id
        """,
        {"board": first["board_id"], "work": work_id},
    )
    second = await calendar_sync.apply_calendar(
        session, CALENDAR, now=datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert second["board_id"] == first["board_id"]
    assert second["added_subject_ids"] == []
    assert (await fetch(session, "SELECT item_count FROM airing_board", {}))[0].item_count == 7
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_board_entry", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_event", {}))[0].n == 1
    third = await calendar_sync.apply_calendar(
        session, CALENDAR, now=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert third["board_id"] != first["board_id"]
    assert third["archived"] == 1
    assert [
        row.status
        for row in await fetch(session, "SELECT status FROM airing_board ORDER BY status", {})
    ] == ["active", "archived"]


@pytest.mark.asyncio
async def test_base_fetch_failure_keeps_existing_board_and_records_error(calendar_runtime):
    session, job_id, _, _, responses = calendar_runtime
    from api.worker.subject_import import import_subject

    await import_subject(session, {"id": 1, "name": "Existing", "type": 2})
    previous = await calendar_sync.apply_calendar(session, CALENDAR)
    await session.commit()
    responses["/v0/subjects/1"] = {"id": 999}
    with pytest.raises(calendar_sync.CalendarError, match="no valid entries"):
        await calendar_tasks.synchronize(
            sync_subject_details=False, job_id=job_id, lease_owner="worker"
        )
    board = (await fetch(session, "SELECT id FROM airing_board WHERE status='active'", {}))[0]
    assert str(board.id) == previous["board_id"]
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_event", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM sync_error", {}))[0].n == 1
    row = (await fetch(session, "SELECT * FROM sync_job WHERE id=:id", {"id": job_id}))[0]
    assert (row.status, row.failed_count) == ("failed", 1)
