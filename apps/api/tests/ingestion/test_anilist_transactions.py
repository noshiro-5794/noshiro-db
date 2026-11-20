from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from api.contexts.ingestion import entities, facts, records
from api.contexts.ingestion import observations as ingestion
from api.db import fetch
from api.integrations.providers import anilist as anilist_provider
from api.worker import anilist_airing, anilist_import, importing, jobs
from api.worker.tasks import maintenance as tasks

MEDIA = {
    "id": 1,
    "idMal": 42,
    "type": "ANIME",
    "format": "TV",
    "status": "RELEASING",
    "title": {
        "romaji": "Romaji",
        "english": "English",
        "native": "原題",
        "userPreferred": "English",
    },
    "description": "Description",
    "synonyms": ["Alias"],
    "isAdult": True,
    "startDate": {"year": 2026, "month": 1, "day": None},
    "endDate": {"year": 2026, "month": 3, "day": 31},
    "episodes": "12",
    "duration": 24,
    "source": "MANGA",
    "season": "WINTER",
    "seasonYear": 2026,
    "averageScore": 81,
    "popularity": 1000,
    "favourites": 10,
    "trending": 20,
    "updatedAt": 1767225600,
    "coverImage": {
        "large": "https://provider.test/poster.jpg",
        "medium": "https://provider.test/thumb.jpg",
    },
    "bannerImage": "https://provider.test/banner.jpg",
    "siteUrl": "https://anilist.co/anime/1",
    "externalLinks": [{"url": "https://example.test", "site": "Official Site"}],
    "genres": ["Drama"],
    "tags": [{"id": 5, "name": "Mystery", "rank": 90}],
    "relations": {
        "edges": [
            {
                "relationType": "SEQUEL",
                "node": {"id": 2, "format": "TV", "title": {"romaji": "Next"}},
            }
        ]
    },
    "characters": {
        "edges": [
            {
                "role": "MAIN",
                "node": {"id": 20, "name": {"full": "Heroine"}},
                "voiceActors": [{"id": 30, "name": {"full": "Person"}}],
            }
        ]
    },
    "staff": {"edges": [{"role": "Director", "node": {"id": 30, "name": {"full": "Person"}}}]},
    "studios": {"edges": [{"node": {"id": 40, "name": "Studio"}}]},
    "airingSchedule": {
        "nodes": [{"id": 1001, "episode": 1, "airingAt": 1767225600, "timeUntilAiring": 100}]
    },
}


@pytest.mark.asyncio
async def test_full_anilist_projection_is_idempotent_and_preserves_metadata(anilist_session):
    session = anilist_session
    entity_id = await anilist_import.import_media(session, MEDIA)
    assert await anilist_import.import_media(session, MEDIA) == entity_id
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert (profile.format, profile.source_material, profile.episode_count) == ("TV", "MANGA", 12)
    assert profile.premiered_on == date(2026, 1, 1)
    assert (await fetch(session, "SELECT audience FROM entity WHERE id=:id", {"id": entity_id}))[
        0
    ].audience == "adult"
    names = await fetch(
        session,
        "SELECT text, language, script, is_official"
        " FROM entity_name WHERE entity_id=:id ORDER BY id",
        {"id": entity_id},
    )
    assert [tuple(row) for row in names] == [
        ("Romaji", "ja", "Latn", True),
        ("English", "en", "Latn", True),
        ("原題", "ja", "Jpan", True),
        ("Alias", "", "", False),
    ]
    counts = {}
    for table in (
        "credit",
        "appearance",
        "voice_performance",
        "entity_term",
        "airing_event",
        "metric_snapshot",
        "provider_revision",
    ):
        counts[table] = (await fetch(session, f"SELECT count(*) AS n FROM {table}", {}))[0].n
    assert counts == {
        "credit": 2,
        "appearance": 1,
        "voice_performance": 1,
        "entity_term": 2,
        "airing_event": 1,
        "metric_snapshot": 4,
        "provider_revision": 3,
    }
    revision = (
        await fetch(
            session,
            "SELECT r.upstream_updated_at"
            " FROM provider_revision r"
            " JOIN provider_record p ON p.latest_revision_id=r.id"
            " JOIN provider_namespace n ON n.id=p.namespace_id"
            " WHERE n.slug='anime' AND p.external_id='1'",
            {},
        )
    )[0]
    assert revision.upstream_updated_at == datetime(2026, 1, 1, tzinfo=UTC)
    episode_record = (
        await fetch(
            session,
            "SELECT canonical_url FROM provider_record p"
            " JOIN provider_namespace n ON n.id=p.namespace_id"
            " WHERE n.slug='episode'",
            {},
        )
    )[0]
    assert episode_record.canonical_url == "https://anilist.co/anime/1"
    link = (
        await fetch(
            session,
            "SELECT label, link_type FROM external_link WHERE url='https://anilist.co/anime/1'",
            {},
        )
    )[0]
    assert tuple(link) == ("AniList", "anilist")


@pytest.mark.asyncio
async def test_next_episode_fallback_is_scoped_by_work(anilist_session):
    session = anilist_session
    for identifier in (1, 2):
        await anilist_import.import_media(
            session, {"id": identifier, "nextAiringEpisode": {"episode": 1, "airingAt": 1767225600}}
        )
    records = await fetch(
        session,
        "SELECT external_id FROM provider_record p"
        " JOIN provider_namespace n ON n.id=p.namespace_id"
        " WHERE n.slug='episode' ORDER BY external_id",
        {},
    )
    assert [row.external_id for row in records] == ["1:1", "2:1"]
    assert (
        await fetch(session, "SELECT count(DISTINCT episode_entity_id) AS n FROM airing_event", {})
    )[0].n == 2


@pytest.mark.asyncio
async def test_countdown_changes_do_not_create_new_episode_revisions(anilist_session):
    session = anilist_session
    await anilist_import.import_media(session, MEDIA)
    changed = {
        **MEDIA,
        "airingSchedule": {
            "nodes": [{**MEDIA["airingSchedule"]["nodes"][0], "timeUntilAiring": 90}]
        },
    }
    await anilist_import.import_media(session, changed)
    count = await fetch(
        session,
        "SELECT count(*) AS n"
        " FROM provider_revision r"
        " JOIN provider_record p ON p.id=r.record_id"
        " JOIN provider_namespace n ON n.id=p.namespace_id"
        " WHERE n.slug='episode'",
        {},
    )
    assert count[0].n == 1


@pytest.mark.asyncio
async def test_embedded_reference_preserves_existing_adult_work(anilist_session):
    session = anilist_session
    entity_id = await anilist_import.import_media(session, {"id": 2, "isAdult": True})
    await anilist_import.import_media(session, MEDIA)
    assert (await fetch(session, "SELECT audience FROM entity WHERE id=:id", {"id": entity_id}))[
        0
    ].audience == "adult"


@pytest.mark.asyncio
async def test_late_airing_failure_rolls_back_the_complete_graph(anilist_session, monkeypatch):
    session = anilist_session
    monkeypatch.setattr(
        anilist_airing, "import_schedule", AsyncMock(side_effect=ValueError("bad schedule"))
    )
    with pytest.raises(ValueError, match="bad schedule"):
        await anilist_import.import_media(session, MEDIA)
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_saved_season_payload_imports_locally_and_rejects_mismatched_identity(
    anilist_session,
):
    session = anilist_session
    await records.record_payload(
        session,
        provider_slug="anilist",
        namespace_slug="season-item",
        resource_type="subject",
        external_id="1",
        payload=MEDIA,
    )
    entity_id = await anilist_import.import_saved_media(session, 1)
    assert await anilist_import.import_saved_media(session, 1) == entity_id
    with pytest.raises(ValueError, match="no persisted seasonal payload"):
        await anilist_import.import_saved_media(session, 2)
    await records.record_payload(
        session,
        provider_slug="anilist",
        namespace_slug="season-item",
        resource_type="subject",
        external_id="2",
        payload={"id": 3},
    )
    with pytest.raises(ValueError, match="payload is inconsistent"):
        await anilist_import.import_saved_media(session, 2)


@pytest.mark.asyncio
async def test_anilist_task_uses_policy_client_lifecycle_and_durable_job(
    anilist_session, monkeypatch
):
    session = anilist_session

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
    client.fetch_media.return_value = MEDIA
    monkeypatch.setattr(anilist_provider, "AniListClient", Mock(return_value=client))
    job_id = str(await jobs.create_job(session, job_type="import_anilist"))
    result = await tasks._import_anilist_media(1, job_id, "worker")
    assert result["provider"] == "anilist"
    client.forbid_storage.assert_called_once_with(forbidden=False)
    client.close.assert_called_once()
    assert (await fetch(session, "SELECT status FROM sync_job WHERE id=:id", {"id": job_id}))[
        0
    ].status == "succeeded"


@pytest.mark.asyncio
async def test_reimport_retires_partial_mapper_and_clears_its_selected_facts(anilist_session):
    session = anilist_session
    written = await records.record_payload(
        session,
        provider_slug="anilist",
        namespace_slug="anime",
        resource_type="subject",
        external_id="1",
        payload={"id": 1},
    )
    observation = await ingestion.record_observation(
        session,
        provider_record_id=written.record_id,
        mapper="anilist.anime",
        mapper_version="anilist-importer-v1",
        normalized_data={"id": 1},
        schema_name="index.work",
        schema_version="1",
    )
    entity = await entities.map_work(
        session, provider_record_id=written.record_id, mapped_data={"subject_type": "anime"}
    )
    await facts.record_fact(
        session,
        entity_id=entity.entity_id,
        observation_id=observation,
        slug="anilist-format",
        name="AniList Format",
        value="TV",
        value_type="string",
        json_pointer="/anilist-format",
    )
    assert await anilist_import.import_media(session, {"id": 1}) == entity.entity_id
    cursors = await fetch(
        session,
        "SELECT mapper FROM provider_current_observation WHERE provider_record_id=:id",
        {"id": written.record_id},
    )
    assert [row.mapper for row in cursors] == ["anilist.media"]
    decision = (
        await fetch(
            session,
            "SELECT selected_fact_id FROM resolution_decision WHERE entity_id=:id AND is_active",
            {"id": entity.entity_id},
        )
    )[0]
    assert decision.selected_fact_id is None
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_observation", {}))[0].n == 2


@pytest.mark.asyncio
async def test_import_request_commits_before_dispatching_the_registered_anilist_task(
    anilist_session, monkeypatch
):
    from inspect import signature

    from api.contexts.synchronization import import_jobs

    session = anilist_session
    published = []

    def publish(task_name, kwargs):
        assert not session.in_transaction()
        assert task_name == "apps.sync.tasks.anilist.import_anilist_media_task"
        signature(tasks.import_anilist_media_task.run).bind(**kwargs)
        assert kwargs["anilist_id"] == 1
        published.append(kwargs)
        return "celery-fixture"

    monkeypatch.setattr(import_jobs, "publish", publish)
    result = await import_jobs.create_import_job(
        session,
        viewer_id=1,
        body={"provider": "anilist", "external_id": "1", "include_related": True},
    )
    assert len(published) == 1
    assert result["id"] == published[0]["job_id"]
    stored = (
        await fetch(
            session, "SELECT celery_task_id FROM sync_job WHERE id=:id", {"id": result["id"]}
        )
    )[0]
    assert stored.celery_task_id == "celery-fixture"


@pytest.mark.asyncio
async def test_mal_import_http_entry_supports_create_list_and_detail(mal_session, monkeypatch):
    from inspect import signature
    from types import SimpleNamespace

    import httpx

    from api.contexts.access.dependencies import staff_user
    from api.contexts.synchronization import import_jobs
    from api.db import get_session
    from api.main import create_app

    session = mal_session
    app = create_app()

    async def sessions():
        yield session

    app.dependency_overrides[get_session] = sessions
    app.dependency_overrides[staff_user] = lambda: SimpleNamespace(id=1)
    calls = []

    def publish(task_name, kwargs):
        assert not session.in_transaction()
        assert task_name == "apps.sync.tasks.mal.import_mal_media_task"
        signature(tasks.import_mal_media_task.run).bind(**kwargs)
        assert kwargs["mal_id"] == 42
        calls.append(kwargs)
        return "celery-fixture"

    monkeypatch.setattr(import_jobs, "publish", publish)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/operations/import-jobs/", json={"provider": "mal", "external_id": "42"}
        )
        assert created.status_code == 202, created.text
        assert created.json()["provider"] == "mal"
        assert len(calls) == 1
        listed = await client.get("/api/v1/operations/import-jobs/?provider=mal")
        assert listed.status_code == 200, listed.text
        assert [row["id"] for row in listed.json()["results"]] == [created.json()["id"]]
        detail = await client.get(f"/api/v1/operations/import-jobs/{created.json()['id']}/")
        assert detail.status_code == 200, detail.text
        assert detail.json()["provider"] == "mal"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("broker offline")])
async def test_import_dispatch_failure_returns_503_and_preserves_failed_job(
    mal_session, monkeypatch, failure
):
    from types import SimpleNamespace

    import httpx

    from api.contexts.access.dependencies import staff_user
    from api.contexts.synchronization import import_jobs
    from api.db import get_session
    from api.main import create_app

    session = mal_session
    app = create_app()

    async def sessions():
        yield session

    app.dependency_overrides[get_session] = sessions
    app.dependency_overrides[staff_user] = lambda: SimpleNamespace(id=1)

    def publish(*args):
        if failure is not None:
            raise failure
        return None

    monkeypatch.setattr(import_jobs, "publish", publish)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/operations/import-jobs/", json={"provider": "mal", "external_id": "42"}
        )
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "sync.task_dispatch_failed"
    row = (await fetch(session, "SELECT status, error FROM sync_job", {}))[0]
    assert row.status == "failed"
    assert row.error == (str(failure) if failure is not None else "Task broker is not configured.")
