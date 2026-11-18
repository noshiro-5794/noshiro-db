from datetime import UTC, datetime

import pytest

from api.contexts.index import resolution
from api.contexts.presentation.fragments import fetch
from api.worker import anilist_import, board_projection, calendar_sync, mal_import, season_sources
from api.worker.subject_import import import_subject
from tests.test_season_sources_transactions import sources as sources

NOW = datetime(2026, 11, 18, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_saved_mal_slot_is_projected_with_evidence_and_replayed(sources):
    session, _, client = sources
    client.fetch_season.return_value = {
        "data": [
            {
                "node": {
                    "id": 2,
                    "title": "Anime",
                    "media_type": "tv",
                    "status": "currently_airing",
                    "broadcast": {"day_of_the_week": "sunday", "start_time": "23:00"},
                    "average_episode_duration": 1440,
                }
            }
        ]
    }
    await season_sources.sync_mal(today=NOW.date())
    work_id = await mal_import.import_saved_anime(session, 2)
    result = await board_projection.rebuild(session, now=NOW)
    assert result["entries"] == result["candidates"] == 1
    assert result["season_key"] == "2026Q4"
    entry = (await fetch(session, "SELECT * FROM airing_board_entry", {}))[0]
    assert entry.work_id == work_id
    assert entry.duration_minutes == 24
    assert entry.precision == "minute"
    assert entry.decision == "source_priority"
    assert entry.source_refs[0]["provider"] == "mal"
    assert entry.source_refs[0]["role"] == "primary"
    again = await board_projection.rebuild(session, now=NOW)
    assert again == result
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_board_entry", {}))[0].n == 1
    observation_id = entry.source_refs[0]["observation_id"]
    client.fetch_season.return_value = {"data": []}
    await season_sources.sync_mal(today=NOW.date())
    assert await fetch(
        session,
        "SELECT id FROM provider_observation WHERE id=:id",
        {"id": observation_id},
    )


@pytest.mark.asyncio
async def test_anilist_minute_evidence_overrides_bangumi_weekday_and_merges_canonical_root(sources):
    session, _, _ = sources
    work_id = await import_subject(session, {"id": 1, "type": 2, "name": "Anime"})
    await calendar_sync.apply_calendar(
        session, [{"weekday": {"id": 1}, "items": [{"id": 1}]}], now=NOW
    )
    imported = await anilist_import.import_media(
        session,
        {
            "id": 2,
            "type": "ANIME",
            "format": "TV",
            "title": {"native": "Anime"},
            "airingSchedule": {"nodes": [{"id": 3, "episode": 1, "airingAt": 1793620800}]},
        },
    )
    await resolution.merge(
        session,
        source_id=imported,
        target_id=work_id,
        method="manual",
        reason="Same anime",
    )
    result = await board_projection.rebuild(session, now=NOW)
    assert result["entries"] == 1
    entry = (await fetch(session, "SELECT * FROM airing_board_entry", {}))[0]
    assert entry.work_id == work_id
    assert entry.precision == "minute"
    assert entry.decision == "consensus"
    assert [item["provider"] for item in entry.source_refs] == ["anilist", "bangumi"]


@pytest.mark.asyncio
async def test_board_retains_previous_season_during_grace_and_archives_after_switch(sources):
    session, _, _ = sources
    await board_projection.rebuild(session, now=datetime(2026, 9, 20, tzinfo=UTC))
    first = (await fetch(session, "SELECT id FROM airing_board WHERE status='active'", {}))[0].id
    pending = await board_projection.rebuild(session, now=datetime(2026, 10, 2, tzinfo=UTC))
    assert pending["board_id"] == str(first)
    assert pending["season_key"] == "2026Q3"
    switched = await board_projection.rebuild(session, now=datetime(2026, 10, 4, tzinfo=UTC))
    assert switched["season_key"] == "2026Q4"
    assert switched["board_id"] != str(first)
    assert (await fetch(session, "SELECT status FROM airing_board WHERE id=:id", {"id": first}))[
        0
    ].status == "archived"


@pytest.mark.asyncio
async def test_later_failure_restores_previous_projection(sources, monkeypatch):
    session, _, client = sources
    client.fetch_season.return_value = {
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
    await season_sources.sync_mal(today=NOW.date())
    await mal_import.import_saved_anime(session, 2)
    await board_projection.rebuild(session, now=NOW)
    entry = (await fetch(session, "SELECT id FROM airing_board_entry", {}))[0].id
    original = (
        await fetch(session, "SELECT metadata FROM airing_board WHERE status='active'", {})
    )[0].metadata
    real_fetch = board_projection.fetch

    async def fail(session, query, params):
        if query.startswith("UPDATE airing_board SET item_count"):
            raise RuntimeError("Injected failure")
        return await real_fetch(session, query, params)

    monkeypatch.setattr(board_projection, "fetch", fail)
    with pytest.raises(RuntimeError):
        await board_projection.rebuild(session, now=NOW)
    current = (await fetch(session, "SELECT metadata FROM airing_board WHERE status='active'", {}))[
        0
    ].metadata
    assert current == original
    assert (await fetch(session, "SELECT id FROM airing_board_entry", {}))[0].id == entry


@pytest.mark.asyncio
async def test_daily_refresh_projects_an_empty_active_board_before_selecting_targets(sources):
    from unittest.mock import AsyncMock

    from api.worker import airing_daily, calendar_write

    session, _, client = sources
    client.fetch_season.return_value = {
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
    await season_sources.sync_mal(today=NOW.date())
    await mal_import.import_saved_anime(session, 2)
    await calendar_write.create_board(
        session, season_key="2026Q4", observation_id=None, item_count=0
    )
    mal_fetcher = AsyncMock(return_value={"id": 2})
    importer = AsyncMock()
    result = await airing_daily.sync_day(
        session,
        now=NOW,
        batch_size=10,
        fetch_anime=mal_fetcher,
        fetch_media=AsyncMock(),
        fetch_subject=AsyncMock(),
        import_anime=importer,
        import_media=AsyncMock(),
        import_subject=AsyncMock(),
    )
    assert result["processed"] == 1
    mal_fetcher.assert_awaited_once_with(2)
    importer.assert_awaited_once_with(session, {"id": 2})
    assert (await fetch(session, "SELECT count(*) AS n FROM airing_board_entry", {}))[0].n == 1
