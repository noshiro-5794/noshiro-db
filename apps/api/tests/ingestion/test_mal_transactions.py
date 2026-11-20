from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from api.contexts.index import resolution
from api.contexts.ingestion import profiles, records
from api.db import fetch
from api.integrations.providers import mal as mal_provider
from api.worker import importing, jobs, mal_import
from api.worker.tasks import maintenance as tasks

PAYLOAD = {
    "id": 1,
    "title": "Anime",
    "media_type": "tv",
    "num_episodes": "12",
    "alternative_titles": {"en": "English", "ja": "原題", "synonyms": ["Alias"]},
    "start_date": "2026-01-01T00:30:00+09:00",
    "end_date": "2026-03-31",
    "synopsis": "Synopsis",
    "main_picture": {"large": "https://provider.test/image.jpg"},
    "broadcast": {"day_of_the_week": "thursday", "start_time": "00:30"},
    "start_season": {"year": 2026, "season": "winter"},
    "status": "currently_airing",
    "mean": 8.2,
    "rank": 100,
    "popularity": 1000,
    "num_list_users": 20000,
    "num_scoring_users": 10000,
    "average_episode_duration": 1420,
}


@pytest.mark.asyncio
async def test_mal_import_preserves_source_fields_metrics_and_replays_once(mal_session):
    session = mal_session
    entity_id = await mal_import.import_anime(session, PAYLOAD)
    assert await mal_import.import_anime(session, PAYLOAD) == entity_id
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert (profile.format, profile.episode_count, profile.premiered_on, profile.ended_on) == (
        "TV",
        12,
        date(2025, 12, 31),
        date(2026, 3, 31),
    )
    link = (
        await fetch(session, "SELECT * FROM external_link WHERE entity_id=:id", {"id": entity_id})
    )[0]
    assert (link.label, link.link_type) == ("MyAnimeList", "mal")
    membership = (
        await fetch(
            session,
            "SELECT inclusion_reason FROM curated_membership WHERE entity_id=:id",
            {"id": entity_id},
        )
    )[0]
    assert membership.inclusion_reason == "MAL anime"
    assert (await fetch(session, "SELECT count(*) AS n FROM metric_snapshot", {}))[0].n == 3
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1
    evidence = await fetch(session, "SELECT json_pointer FROM fact_evidence", {})
    assert {row.json_pointer for row in evidence} == set(mal_import.FACT_POINTERS.values())
    await mal_import.import_anime(session, {"id": 1})
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert profile.format == ""
    assert profile.episode_count is None
    assert profile.premiered_on == date(2025, 12, 31)
    assert profile.ended_on == date(2026, 3, 31)


@pytest.mark.asyncio
async def test_saved_schedule_payload_imports_without_provider_io(mal_session):
    session = mal_session
    record = await records.record_payload(
        session,
        provider_slug="mal",
        namespace_slug="schedule-item",
        resource_type="subject",
        external_id="1",
        payload=PAYLOAD,
    )
    entity_id = await mal_import.import_saved_anime(session, 1)
    assert await mal_import.import_saved_anime(session, 1) == entity_id
    await fetch(
        session,
        "UPDATE provider_record SET status='missing' WHERE id=:id RETURNING id",
        {"id": record.record_id},
    )
    with pytest.raises(ValueError, match="no persisted schedule payload"):
        await mal_import.import_saved_anime(session, 1)


@pytest.mark.asyncio
async def test_saved_payload_id_mismatch_is_rejected(mal_session):
    session = mal_session
    await records.record_payload(
        session,
        provider_slug="mal",
        namespace_slug="schedule-item",
        resource_type="subject",
        external_id="1",
        payload={"id": 2},
    )
    with pytest.raises(ValueError, match="payload is inconsistent"):
        await mal_import.import_saved_anime(session, 1)
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_late_failure_rolls_back_projection_and_keeps_callers_changes(
    mal_session, monkeypatch
):
    session = mal_session
    monkeypatch.setattr(resolution, "resolve", AsyncMock(side_effect=ValueError("bad redirect")))
    with pytest.raises(ValueError, match="bad redirect"):
        await mal_import.import_anime(session, PAYLOAD)
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider WHERE slug='mal'", {}))[
        0
    ].n == 1


@pytest.mark.asyncio
async def test_mal_task_entry_enforces_policy_closes_client_and_finishes_job(
    mal_session, monkeypatch
):
    session = mal_session

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
    client.fetch_anime.return_value = PAYLOAD
    monkeypatch.setattr(mal_provider, "MALClient", Mock(return_value=client))
    job_id = str(await jobs.create_job(session, job_type="import_mal"))
    result = await tasks._import_mal_media(1, job_id, "worker")
    assert result["external_id"] == 1
    assert result["provider"] == "mal"
    client.forbid_storage.assert_called_once_with(forbidden=False)
    client.close.assert_called_once()
    job = (
        await fetch(
            session, "SELECT status, synced_count FROM sync_job WHERE id=:id", {"id": job_id}
        )
    )[0]
    assert (job.status, job.synced_count) == ("succeeded", 1)


@pytest.mark.asyncio
async def test_profile_and_collection_defaults_preserve_existing_callers(mal_session):
    session = mal_session
    entity_id = await mal_import.import_anime(session, PAYLOAD)
    await profiles.upsert_anime_profile(session, work_entity_id=entity_id, source_material="Manga")
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert (profile.format, profile.episode_count, profile.source_material) == ("TV", 12, "Manga")

    await fetch(
        session,
        "UPDATE curated_collection SET name='Custom Anime' WHERE slug='anime' RETURNING id",
        {},
    )
    await mal_import.import_anime(session, PAYLOAD)
    assert (await fetch(session, "SELECT name FROM curated_collection WHERE slug='anime'", {}))[
        0
    ].name == "Custom Anime"


@pytest.mark.asyncio
async def test_reimport_returns_resolved_identity_after_a_merge(mal_session):
    session = mal_session
    source = await mal_import.import_anime(session, PAYLOAD)
    target = await mal_import.import_anime(session, {**PAYLOAD, "id": 2})
    await resolution.merge(
        session, source_id=source, target_id=target, method="rule", reason="fixture"
    )
    assert await mal_import.import_anime(session, PAYLOAD) == target
    representations = await fetch(
        session,
        "SELECT entity_id FROM entity_representation WHERE entity_id=:id AND is_active",
        {"id": source},
    )
    assert len(representations) == 1
