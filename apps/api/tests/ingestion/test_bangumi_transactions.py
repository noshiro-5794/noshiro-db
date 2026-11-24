from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from api.contexts.identity import vndb
from api.contexts.index import resolution
from api.contexts.ingestion import profiles
from api.contexts.synchronization.terms import normalize_key
from api.db import fetch
from api.integrations.providers.vndb import VNDBImportBatch
from api.worker import subject_import
from api.worker.vndb_import import import_batch

SUBJECT = {
    "id": 1,
    "type": 2,
    "name": " Original ",
    "name_cn": " 标题 ",
    "summary": " Summary ",
    "date": "2026-01-01",
    "platform": "TV",
    "nsfw": True,
    "series": False,
    "total_episodes": 12,
    "eps": 0,
    "meta_tags": [" Sci-Fi ", "DRAMA"],
    "infobox": [{"key": " Alias ", "value": [{"v": "Alternative"}]}],
    "images": {
        "large": "https://provider.test/poster.jpg",
        "medium": "https://provider.test/thumb.jpg",
    },
    "rating": {"score": 8.2, "rank": 100, "total": 2000},
}


@pytest.mark.asyncio
async def test_subject_metadata_names_facts_and_rating_history_match_source(bangumi_session):
    session = bangumi_session
    entity_id = await subject_import.import_subject(session, SUBJECT)
    await fetch(
        session,
        "UPDATE entity_representation SET confidence=0.5 WHERE entity_id=:id RETURNING id",
        {"id": entity_id},
    )
    assert await subject_import.import_subject(session, SUBJECT) == entity_id
    assert (
        await fetch(
            session,
            "SELECT confidence FROM entity_representation WHERE entity_id=:id",
            {"id": entity_id},
        )
    )[0].confidence == 1
    names = await fetch(
        session, "SELECT text, language, script, kind, is_original FROM entity_name ORDER BY id", {}
    )
    assert [tuple(row) for row in names] == [
        ("Original", "", "", "original", True),
        ("标题", "zh-Hans", "Hans", "translated", False),
    ]
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert (profile.episode_count, profile.premiered_on) == (12, date(2026, 1, 1))
    ratings = await fetch(
        session,
        "SELECT metric, value FROM ranking.provider_metric ORDER BY observed_at, metric",
        {},
    )
    assert [tuple(row) for row in ratings] == [
        ("rank", Decimal(100)),
        ("score", Decimal("8.2")),
        ("votes", Decimal(2000)),
    ] * 2
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1
    values = await fetch(
        session,
        "SELECT p.slug, f.value, e.json_pointer FROM fact f"
        " JOIN predicate p ON p.id=f.predicate_id"
        " JOIN fact_evidence e ON e.fact_id=f.id ORDER BY p.slug",
        {},
    )
    by_slug = {row.slug: (row.value, row.json_pointer) for row in values}
    assert "provider-tags" not in by_slug
    assert by_slug["provider-infobox"] == ([{"key": "Alias", "value": ["Alternative"]}], "/infobox")
    decisions = (
        await fetch(
            session,
            "SELECT count(*) AS total, count(*) FILTER (WHERE is_active) AS active"
            " FROM resolution_decision WHERE entity_id = :id",
            {"id": entity_id},
        )
    )[0]
    assert decisions.total == decisions.active > 0


@pytest.mark.asyncio
async def test_missing_episode_count_clears_only_the_owned_profile_field(bangumi_session):
    session = bangumi_session
    entity_id = await subject_import.import_subject(session, SUBJECT)
    await profiles.upsert_anime_profile(
        session, work_entity_id=entity_id, media_format="OVA", source_material="MANGA"
    )
    await subject_import.import_subject(session, {"id": 1, "type": 2})
    profile = (
        await fetch(session, "SELECT * FROM anime_profile WHERE work_id=:id", {"id": entity_id})
    )[0]
    assert profile.episode_count is None
    assert (profile.format, profile.source_material, profile.premiered_on) == (
        "OVA",
        "MANGA",
        date(2026, 1, 1),
    )


@pytest.mark.asyncio
async def test_bangumi_tags_classify_visual_novels_without_projecting_tag_facts(bangumi_session):
    session = bangumi_session
    payload = {"id": 1, "type": 4, "meta_tags": ["galgame"]}
    entity_id = await subject_import.import_subject(session, payload)
    works = await fetch(
        session, "SELECT work_type FROM work WHERE entity_id=:id", {"id": entity_id}
    )
    assert [row.work_type for row in works] == ["galgame"]
    assert not await fetch(session, "SELECT id FROM predicate WHERE slug='provider-tags'", {})


@pytest.mark.asyncio
async def test_global_aliases_do_not_rewrite_source_work_fields(bangumi_session):
    session = bangumi_session
    for source, preferred, reviewed in (
        ("\uff30\uff23", "Windows", True),
        ("\uff21\uff4c\uff49\uff41\uff53", "别名", True),
        ("Sci-Fi", "Science Fiction", True),
        ("DRAMA", "Incorrect unreviewed term", False),
    ):
        await fetch(
            session,
            """
            INSERT INTO taxonomy_alias
              (vocabulary, provider_namespace_id, source_text, normalized_key, preferred_term,
               language, script, confidence, is_reviewed, origin, term_id, created_at, updated_at)
            VALUES ('legacy', NULL, :source, :key, :preferred, '', '', 1, :reviewed,
                    'manual', NULL, now(), now())
            RETURNING id
        """,
            {
                "source": source,
                "key": normalize_key(source),
                "preferred": preferred,
                "reviewed": reviewed,
            },
        )
    await subject_import.import_subject(session, {**SUBJECT, "platform": "\uff30\uff23"})
    values = await fetch(
        session, "SELECT p.slug, f.value FROM fact f JOIN predicate p ON p.id=f.predicate_id", {}
    )
    by_slug = {row.slug: row.value for row in values}
    assert by_slug["platform"] == "\uff30\uff23"
    assert "provider-tags" not in by_slug
    assert by_slug["provider-infobox"] == [{"key": "Alias", "value": ["Alternative"]}]


@pytest.mark.asyncio
async def test_cached_and_placeholder_work_identity_promotes_without_duplication(bangumi_session):
    session = bangumi_session
    placeholder = await subject_import.provide_subject(session, 1)
    assert await subject_import.provide_subject(session, 1) == placeholder
    assert (await fetch(session, "SELECT raw_state FROM provider_record", {}))[
        0
    ].raw_state == "legacy"
    assert await subject_import.import_subject(session, SUBJECT) == placeholder
    assert await subject_import.provide_subject(session, 1) == placeholder
    assert (await fetch(session, "SELECT raw_state FROM provider_record", {}))[0].raw_state == "raw"
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1


@pytest.mark.asyncio
async def test_late_identity_failure_rolls_back_complete_projection(bangumi_session, monkeypatch):
    session = bangumi_session
    monkeypatch.setattr(
        vndb, "observe_bangumi", AsyncMock(side_effect=ValueError("identity failed"))
    )
    with pytest.raises(ValueError, match="identity failed"):
        await subject_import.import_subject(session, SUBJECT)
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("vndb_first", [True, False])
async def test_explicit_ids_bind_both_source_arrival_orders(
    vndb_session, register_provider, vndb_first
):
    session = vndb_session
    await register_provider("bangumi", "Bangumi")
    payload = {
        "id": 1,
        "type": 4,
        "meta_tags": ["galgame"],
        "infobox": [{"key": "VNDB", "value": "https://vndb.org/v17"}],
    }
    batch = VNDBImportBatch(work={"id": "v17"})
    if vndb_first:
        vndb_id = await import_batch(session, "v17", batch)
        bangumi_id = await subject_import.import_subject(session, payload)
    else:
        bangumi_id = await subject_import.import_subject(session, payload)
        vndb_id = await import_batch(session, "v17", batch)
    assert await resolution.resolve(session, bangumi_id) == await resolution.resolve(
        session, vndb_id
    )
    assert (await fetch(session, "SELECT outcome FROM candidate_decision", {}))[0].outcome == "bind"
    evidence = await fetch(
        session,
        "SELECT json_pointer FROM fact_evidence e JOIN fact f ON f.id=e.fact_id"
        " JOIN predicate p ON p.id=f.predicate_id"
        " WHERE p.slug='external-id-vndb'",
        {},
    )
    assert [row.json_pointer for row in evidence] == ["/infobox/0/value"]


@pytest.mark.asyncio
@pytest.mark.parametrize("forbidden", [False, True])
async def test_refresh_entry_enforces_storage_policy_and_closes_transport(
    bangumi_session, monkeypatch, forbidden
):
    from contextlib import asynccontextmanager

    import httpx

    from api.integrations.providers import bangumi
    from api.worker.tasks import maintenance as tasks

    session = bangumi_session
    await subject_import.import_subject(session, SUBJECT)
    await fetch(
        session,
        "UPDATE provider SET storage_policy=:policy WHERE slug='bangumi' RETURNING id",
        {"policy": "forbidden" if forbidden else "allowed"},
    )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={**SUBJECT, "name": "Updated"})

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://provider.test")
    client = bangumi.BangumiClient(http=http)
    monkeypatch.setattr(bangumi, "BangumiClient", lambda: client)

    @asynccontextmanager
    async def sessions():
        yield session
        await session.commit()

    monkeypatch.setattr(tasks, "session_scope", sessions)
    result = await tasks._refresh_bangumi_subjects(1)
    assert result["refreshed"] == int(not forbidden)
    assert result["failed"] == int(forbidden)
    assert len(requests) == int(not forbidden)
    assert http.is_closed


@pytest.mark.asyncio
async def test_global_alias_changes_do_not_create_new_source_observations(
    bangumi_session,
):
    session = bangumi_session
    entity_id = await subject_import.import_subject(session, SUBJECT)
    first = (await fetch(session, "SELECT observation_id FROM provider_current_observation", {}))[
        0
    ].observation_id
    await fetch(
        session,
        """
        INSERT INTO taxonomy_alias
          (vocabulary, provider_namespace_id, source_text, normalized_key, preferred_term,
           language, script, confidence, is_reviewed, origin, term_id, created_at, updated_at)
        VALUES ('legacy', NULL, 'Alias', 'alias', '别名', '', '', 1, true,
                'manual', NULL, now(), now()) RETURNING id
    """,
        {},
    )
    assert await subject_import.import_subject(session, SUBJECT) == entity_id
    current = (await fetch(session, "SELECT observation_id FROM provider_current_observation", {}))[
        0
    ].observation_id
    assert current == first
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1
    selected = await fetch(
        session,
        """
        SELECT f.value FROM resolution_decision d JOIN predicate p ON p.id=d.predicate_id
        JOIN fact f ON f.id=d.selected_fact_id
        WHERE d.is_active AND p.slug='provider-infobox'
    """,
        {},
    )
    assert [row.value for row in selected] == [[{"key": "Alias", "value": ["Alternative"]}]]
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_observation", {}))[0].n == 1
