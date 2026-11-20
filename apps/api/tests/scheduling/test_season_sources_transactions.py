from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import Mock

import pytest

from api.db import fetch
from api.integrations.providers.errors import ProviderError
from api.worker import season_sources, snapshot_retention
from api.worker.subject_import import import_subject


@pytest.fixture
async def sources(integration_session, register_provider, monkeypatch):
    await register_provider("anilist", "AniList")
    await register_provider("mal", "MyAnimeList")
    await register_provider("bangumi", "Bangumi")
    session = integration_session

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(season_sources, "session_scope", scope)
    anilist = Mock()
    mal = Mock()
    anilist.fetch_airing_page.return_value = {
        "pageInfo": {"hasNextPage": False},
        "media": [{"id": 1, "status": "RELEASING"}],
    }
    mal.fetch_season.return_value = {
        "data": [{"node": {"id": 2, "broadcast": {"start_time": "23:00"}}}],
        "paging": {},
    }
    monkeypatch.setattr(season_sources, "AniListClient", lambda: anilist)
    monkeypatch.setattr(season_sources, "MALClient", lambda: mal)
    return session, anilist, mal


@pytest.mark.asyncio
async def test_airing_pages_filter_horizon_deduplicate_and_compact_snapshot(sources):
    session, client, _ = sources
    client.fetch_airing_page.side_effect = [
        {
            "pageInfo": {"hasNextPage": True},
            "media": [
                {"id": 1, "status": "RELEASING"},
                {"id": 2, "status": "NOT_YET_RELEASED", "startDate": {"year": 2035}},
            ],
        },
        {
            "pageInfo": {"hasNextPage": False},
            "media": [
                {"id": 1, "status": "RELEASING", "title": {"native": "Updated"}},
                {"id": 3, "startDate": {"year": 2026, "month": 11}},
            ],
        },
    ]
    first = await season_sources.sync_anilist(today=date(2026, 11, 18))
    assert first["items_seen"] == first["items_recorded"] == 2
    assert first["season_key"] == "fall:2026"
    assert first["pages"] == 2
    assert client.fetch_airing_page.call_args_list[1].kwargs["cursor"] == "2"
    client.fetch_airing_page.side_effect = None
    second = await season_sources.sync_anilist(today=date(2026, 11, 18))
    assert second["changed"] is True
    rows = await fetch(
        session,
        "SELECT count(*) AS n FROM provider_revision WHERE record_id=:id",
        {"id": first["season_record_id"]},
    )
    assert rows[0].n == 1
    unchanged = await season_sources.sync_anilist(today=date(2026, 11, 18))
    assert unchanged["changed"] is False
    assert client.close.call_count == 3


@pytest.mark.asyncio
async def test_mal_uses_node_offsets_and_normalized_broadcast_facts(sources):
    session, _, client = sources
    client.fetch_season.side_effect = [
        {
            "data": [{"node": {"id": 1}}, {"id": 2}],
            "paging": {"next": "next-page"},
        },
        {
            "data": [
                {
                    "node": {
                        "id": 2,
                        "broadcast": {"day_of_the_week": "sunday", "start_time": "23:00"},
                        "average_episode_duration": 1440,
                    }
                }
            ],
            "paging": {},
        },
    ]
    result = await season_sources.sync_mal(today=date(2026, 11, 18))
    assert result["season"]["season_key"] == "2026Q4"
    assert result["season"]["items_seen"] == 2
    assert client.fetch_season.call_args_list[1].kwargs["offset"] == 2
    observed = (
        await fetch(
            session,
            "SELECT normalized_data FROM provider_observation WHERE provider_record_id=:id",
            {"id": result["season"]["schedule_record_id"]},
        )
    )[0].normalized_data
    assert observed["items"][1]["duration_minutes"] == 24
    assert observed["items"][1]["timezone"] == "Asia/Tokyo"
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_snapshot_retention_preserves_referenced_observation(sources):
    session, client, _ = sources
    first = await season_sources.sync_anilist(today=date(2026, 11, 18))
    observation = (await fetch(session, "SELECT id FROM provider_observation", {}))[0].id
    work_id = await import_subject(session, {"id": 100, "type": 2, "name": "Title"})
    await fetch(
        session,
        "UPDATE entity_name SET observation_id=:observation WHERE entity_id=:work RETURNING id",
        {"observation": observation, "work": work_id},
    )
    await session.commit()
    client.fetch_airing_page.return_value = {"media": [{"id": 2, "status": "RELEASING"}]}
    await season_sources.sync_anilist(today=date(2026, 11, 18))
    result = await snapshot_retention.retain_current(session, first["season_record_id"])
    assert result == {"deleted_revisions": 0, "deleted_observations": 0}
    assert await fetch(
        session, "SELECT id FROM provider_observation WHERE id=:id", {"id": observation}
    )


@pytest.mark.asyncio
async def test_provider_failure_closes_client_without_partial_capture(sources):
    session, client, _ = sources
    client.fetch_airing_page.side_effect = [
        {"pageInfo": {"hasNextPage": True}, "media": [{"id": 1, "status": "RELEASING"}]},
        ProviderError("Unavailable"),
    ]
    with pytest.raises(ProviderError):
        await season_sources.sync_anilist()
    client.close.assert_called_once()
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0


@pytest.mark.asyncio
async def test_item_write_failure_rolls_back_snapshot_and_observation(sources, monkeypatch):
    session, _, _ = sources

    async def fail(*args):
        raise RuntimeError("Item persistence failed")

    monkeypatch.setattr(season_sources, "record_items", fail)
    with pytest.raises(RuntimeError):
        await season_sources.sync_mal()
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0


@pytest.mark.asyncio
async def test_retention_reference_inventory_matches_schema(sources):
    session, _, _ = sources
    references = await fetch(
        session,
        "SELECT t.relname,a.attname FROM pg_constraint c "
        "JOIN pg_class t ON t.oid=c.conrelid "
        "JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey) "
        "WHERE c.contype='f' AND c.confrelid='provider_observation'::regclass",
        {},
    )
    protected = {(row.relname, row.attname) for row in references}
    protected.remove(("provider_current_observation", "observation_id"))
    assert protected == set(snapshot_retention.OBSERVATION_REFERENCES)


@pytest.mark.asyncio
async def test_retention_keeps_entity_record_history(sources):
    session, _, _ = sources
    work_id = await import_subject(session, {"id": 100, "type": 2, "name": "Title"})
    await import_subject(session, {"id": 100, "type": 2, "name": "Changed"})
    record = (
        await fetch(
            session,
            "SELECT provider_record_id FROM entity_representation WHERE entity_id=:id",
            {"id": work_id},
        )
    )[0].provider_record_id
    result = await snapshot_retention.retain_current(session, record)
    assert result == {"deleted_revisions": 0, "deleted_observations": 0}
    assert (
        await fetch(
            session,
            "SELECT count(*) AS n FROM provider_revision WHERE record_id=:id",
            {"id": record},
        )
    )[0].n == 2
