from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid5

import pytest

from api.db import fetch
from api.worker import bangumi_sync
from api.worker.bangumi_entities import import_entity
from api.worker.bangumi_episodes import EPISODE_NAMESPACE, import_episodes

SUBJECT = {"id": 1, "type": 2, "name": "Anime", "nsfw": True, "total_episodes": 12}
EPISODES = [
    {
        "id": 1001,
        "name": "Episode one",
        "name_cn": "第一集",
        "type": 0,
        "ep": 1.5,
        "sort": 1.5,
        "duration_seconds": 1200,
        "duration": "20:00",
        "airdate": "2026-01-01",
        "disc": 0,
        "comment": 2,
    }
]
SUBJECTS = [{"id": 2, "relation": "续作"}]
STAFF = [{"id": 20, "name": "Studio credit", "relation": "动画制作"}]
CHARACTERS = [{"id": 30, "relation": "主角", "actors": [{"id": 21, "name": "Actor credit"}]}]
PEOPLE = {
    "20": {"id": 20, "name": "Studio", "type": 2, "summary": "Studio biography"},
    "21": {"id": 21, "name": "Actor", "type": 1, "summary": "Person biography"},
}
CHARACTER_DETAILS = {
    "30": {
        "id": 30,
        "name": "Heroine",
        "type": 1,
        "summary": "Biography",
        "images": {"large": "https://provider.test/heroine.jpg"},
    }
}


def batch():
    return bangumi_sync.SubjectBatch(
        SUBJECT, EPISODES, SUBJECTS, STAFF, CHARACTERS, PEOPLE, CHARACTER_DETAILS
    )


@pytest.mark.asyncio
async def test_complete_graph_projection_preserves_ids_subtypes_and_source_evidence(
    bangumi_session,
):
    session = bangumi_session
    result = await bangumi_sync.project_batch(session, 1, batch())
    assert await bangumi_sync.project_batch(session, 1, batch()) == result
    assert result == {
        "subject_id": result["subject_id"],
        "bangumi_id": 1,
        "title": "Anime",
        "subject_type": "anime",
        "episode_synced": True,
        "staff_count": 2,
        "character_count": 1,
        "related_subject_count": 1,
    }
    episode = (await fetch(session, "SELECT id, audience FROM entity WHERE kind='episode'", {}))[0]
    assert episode.id == uuid5(EPISODE_NAMESPACE, "episode:1001")
    assert episode.audience == "adult"
    for table, expected in (
        ("appearance", 1),
        ("credit", 1),
        ("voice_performance", 1),
        ("person", 1),
        ("organization", 1),
        ("provider_revision", 9),
    ):
        assert (await fetch(session, f"SELECT count(*) AS n FROM {table}", {}))[0].n == expected
    evidence = await fetch(
        session,
        "SELECT r.relation_type,e.json_pointer FROM entity_relation_evidence e "
        "JOIN entity_relation r ON r.id=e.relation_id ORDER BY r.relation_type",
        {},
    )
    assert [tuple(row) for row in evidence] == [("has-episode", "/items/0"), ("sequel", "/items/0")]
    values = await fetch(
        session,
        "SELECT p.slug,f.value FROM fact f JOIN predicate p ON p.id=f.predicate_id "
        "WHERE f.entity_id=:id",
        {"id": episode.id},
    )
    by_slug = {row.slug: row.value for row in values}
    assert by_slug["episode-number"] == "1.5"
    assert by_slug["duration-seconds"] == 1200.0
    assert by_slug["episode-type"] == "EP"


@pytest.mark.asyncio
async def test_duplicate_episode_ids_keep_the_last_payload_and_original_pointer(bangumi_session):
    session = bangumi_session
    episodes = [{**EPISODES[0], "name": "Earlier"}, None, {**EPISODES[0], "name": "Latest"}]
    await bangumi_sync.project_batch(session, 1, replace(batch(), episodes=episodes))
    pointers = await fetch(
        session,
        "SELECT e.json_pointer FROM entity_relation_evidence e "
        "JOIN entity_relation r ON r.id=e.relation_id "
        "WHERE r.relation_type='has-episode'",
        {},
    )
    assert [row.json_pointer for row in pointers] == ["/items/2"]
    assert (await fetch(session, "SELECT count(*) AS n FROM entity WHERE kind='episode'", {}))[
        0
    ].n == 1


@pytest.mark.asyncio
async def test_full_graph_failure_rolls_back_metadata_and_embedded_identities(
    bangumi_session, monkeypatch
):
    session = bangumi_session
    monkeypatch.setattr(
        bangumi_sync, "import_entity", AsyncMock(side_effect=ValueError("bad person"))
    )
    with pytest.raises(ValueError, match="bad person"):
        await bangumi_sync.project_batch(session, 1, batch())
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0


@pytest.mark.asyncio
async def test_reimport_does_not_downgrade_character_or_episode_audience(bangumi_session):
    session = bangumi_session
    result = await bangumi_sync.project_batch(session, 1, batch())
    character = (await fetch(session, "SELECT id FROM entity WHERE kind='character'", {}))[0].id
    await fetch(
        session, "UPDATE entity SET audience='adult' WHERE id=:id RETURNING id", {"id": character}
    )
    await import_entity(session, CHARACTER_DETAILS["30"], "character")
    await fetch(
        session,
        "UPDATE entity SET audience='general' WHERE id=:id RETURNING id",
        {"id": result["subject_id"]},
    )
    await import_episodes(session, result["subject_id"], "1", EPISODES)
    rows = await fetch(
        session,
        "SELECT audience FROM entity WHERE kind=ANY(:kinds)",
        {"kinds": ["character", "episode"]},
    )
    assert [row.audience for row in rows] == ["adult", "adult"]


@pytest.mark.asyncio
async def test_global_aliases_do_not_rewrite_source_roles(bangumi_session):
    session = bangumi_session
    await bangumi_sync.project_batch(session, 1, batch())
    await fetch(
        session,
        """
        INSERT INTO taxonomy_alias
          (vocabulary, provider_namespace_id, source_text, normalized_key, preferred_term,
           language, script, confidence, is_reviewed, origin, term_id, created_at, updated_at)
        VALUES ('legacy', NULL, '主角', '主角', '主演', '', '', 1, true,
                'manual', NULL, now(), now())
        RETURNING id
    """,
        {},
    )
    await bangumi_sync.project_batch(session, 1, batch())
    roles = await fetch(
        session,
        "SELECT a.role FROM appearance a JOIN provider_current_observation c "
        "ON c.observation_id=a.observation_id WHERE c.mapper='bangumi.subject-characters'",
        {},
    )
    assert [row.role for row in roles] == ["主角"]
    assert (await fetch(session, "SELECT count(*) AS n FROM appearance", {}))[0].n == 1
