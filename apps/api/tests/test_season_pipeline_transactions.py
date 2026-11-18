from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest

from api.contexts.presentation.fragments import fetch
from api.worker import board_projection, season_tasks
from tests.test_season_sources_transactions import sources as sources


@pytest.fixture
async def season_runtime(sources, monkeypatch):
    session, anilist, mal = sources
    from api.worker import season_sources

    monkeypatch.setattr(season_tasks, "session_scope", season_sources.session_scope)
    monkeypatch.setattr(season_sources, "local_today", lambda: date(2026, 11, 18))
    generated = AsyncMock(return_value={"created_ids": ["candidate"], "candidates_created": 1})
    monkeypatch.setattr(season_tasks, "candidates", generated)
    sender = AsyncMock(return_value="evaluation-task")
    monkeypatch.setattr(season_tasks.dispatch, "enqueue", sender)
    anilist.fetch_airing_page.return_value = {
        "media": [{"id": 1, "status": "RELEASING", "format": "TV", "title": {"native": "Anime"}}]
    }
    mal.fetch_season.return_value = {
        "data": [
            {
                "node": {
                    "id": 2,
                    "title": "Anime",
                    "media_type": "tv",
                    "status": "currently_airing",
                    "broadcast": {"day_of_the_week": "sunday", "start_time": "23:00"},
                }
            }
        ]
    }
    return session, anilist, mal, generated, sender


@pytest.mark.asyncio
async def test_season_pipeline_promotes_sources_and_deduplicates_evaluation_dispatch(
    season_runtime,
):
    session, _, _, generated, sender = season_runtime
    result = await season_tasks.season_pipeline(evaluate=True)
    assert result["overall"] == "succeeded"
    assert result["anilist_imported"] == 1
    assert result["mal"]["imported_entities"] == 1
    assert result["ai_evaluations_dispatched"] == 1
    assert result["board"]["status"] == "succeeded"
    sender.assert_awaited_once()
    assert generated.await_count == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 2
    replay = await season_tasks.season_pipeline()
    assert replay["anilist_imported"] == replay["mal"]["imported_entities"] == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM work", {}))[0].n == 2


@pytest.mark.asyncio
async def test_source_failure_is_isolated_and_successful_source_still_projects(season_runtime):
    _, client, _, _, sender = season_runtime
    client.fetch_airing_page.side_effect = RuntimeError("Source unavailable")
    result = await season_tasks.season_pipeline()
    assert result["overall"] == "partial"
    assert result["sources"]["anilist"]["status"] == "failed"
    assert result["sources"]["mal"]["status"] == "succeeded"
    assert result["board"]["status"] == "succeeded"
    sender.assert_not_awaited()


@pytest.mark.asyncio
async def test_saved_mal_pipeline_avoids_network_and_handles_invalid_payload_ids(season_runtime):
    session, _, client, _, _ = season_runtime
    from api.worker import records

    for identifier in ["2", "invalid"]:
        await records.record_payload(
            session,
            provider_slug="mal",
            namespace_slug="schedule-item",
            resource_type="subject",
            external_id=identifier,
            payload={"id": 2, "title": "Anime"},
        )
    result = await season_tasks.mal_pipeline(fetch_season=False)
    assert result["season"] is None
    assert result["saved_anime_ids"] == 2
    assert result["imported_entities"] == 1
    client.fetch_season.assert_not_called()


@pytest.mark.asyncio
async def test_rollover_does_nothing_for_current_board(season_runtime):
    session, anilist, mal, _, _ = season_runtime
    await board_projection.rebuild(session)
    result = await season_tasks.rollover()
    assert result == {"action": "none", "season_key": "2026Q4"}
    anilist.fetch_airing_page.assert_not_called()
    mal.fetch_season.assert_not_called()


@pytest.mark.asyncio
async def test_rollover_prefetch_keeps_active_board_until_grace_then_retires_old_shards(
    season_runtime, monkeypatch
):
    from unittest.mock import Mock

    from api.worker import airing_daily, season_sources

    session, _, _, _, _ = season_runtime
    old = await board_projection.rebuild(session, now=datetime(2026, 9, 20, tzinfo=UTC))
    await airing_daily.start_window(
        session, shard="airing_daily:2026-09-20:2026Q3", total_count=3, batch_size=1
    )
    await airing_daily.start_window(
        session, shard="airing_daily:2026-10-04:2026Q4", total_count=3, batch_size=1
    )
    client = Mock()
    client.fetch_calendar.return_value = [{"weekday": {"id": 1}, "items": [{"id": 100}]}]
    monkeypatch.setattr(season_sources, "BangumiClient", lambda: client)
    monkeypatch.setattr(season_sources, "local_today", lambda: date(2026, 10, 2))
    result = await season_tasks.rollover()
    assert result["action"] == "prefetched"
    assert result["active_season"] == "2026Q3"
    active = (
        await fetch(session, "SELECT id,season_key FROM airing_board WHERE status='active'", {})
    )[0]
    assert str(active.id) == old["board_id"]
    assert active.season_key == "2026Q3"
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_observation", {}))[0].n == 3
    client.close.assert_called_once()
    monkeypatch.setattr(season_sources, "local_today", lambda: date(2026, 10, 4))
    monkeypatch.setattr(season_tasks.calendar_tasks, "synchronize", AsyncMock(return_value={}))
    switched = await season_tasks.rollover()
    assert switched["action"] == "switched"
    assert switched["retired_sync_shards"] == 1
    states = await fetch(
        session,
        "SELECT shard,status FROM sync_state WHERE task_name='airing_daily' ORDER BY shard",
        {},
    )
    assert [row.status for row in states] == ["finished", "running"]


@pytest.mark.asyncio
async def test_no_board_initializes_through_full_pipeline(season_runtime):
    result = await season_tasks.rollover()
    assert result["action"] == "initialized"
    assert result["pipeline"]["overall"] == "succeeded"
