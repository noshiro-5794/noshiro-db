from uuid import uuid4

import pytest

from api.contexts.ingestion import entities, observations, records, relations
from api.contexts.presentation.episodes import episode_ids, episode_page
from api.db import fetch
from api.worker.subject_import import import_subject


async def _episode(session, work_id, provider: str):
    written = await records.record_payload(
        session,
        provider_slug=provider,
        namespace_slug="episode",
        resource_type="episode",
        external_id="1",
        payload={"id": 1},
    )
    observed = await observations.record_observation(
        session,
        provider_record_id=written.record_id,
        mapper=f"{provider}.episode",
        mapper_version="v1",
        normalized_data={"id": 1},
        schema_name="index.episode",
        schema_version="1",
    )
    episode = uuid4()
    await fetch(
        session,
        "INSERT INTO entity"
        " (id,kind,lifecycle,visibility,audience,spoiler_level,created_at,updated_at)"
        " VALUES (:id,'episode','active','public','general',0,now(),now()) RETURNING id",
        {"id": episode},
    )
    await entities.upsert_representation(
        session, provider_record_id=written.record_id, entity_id=episode
    )
    await relations.relation(
        session,
        work_id,
        episode,
        observed,
        relation_type="has-episode",
        json_pointer="",
        raw_relation="has-episode",
    )
    return episode


@pytest.mark.asyncio
async def test_episode_list_falls_back_as_a_unit(bangumi_session, register_provider):
    await register_provider("anilist", "AniList")
    session = bangumi_session
    work_id = await import_subject(session, {"id": 1, "type": 2, "name": "Work"})
    bangumi = await _episode(session, work_id, "bangumi")
    anilist = await _episode(session, work_id, "anilist")
    ids = [str(work_id)]
    assert set(await episode_ids(session, ids, public_only=False)) == {bangumi, anilist}

    count, episodes = await episode_page(session, cluster=ids, language="", page=1, page_size=10)
    assert count == 1
    assert [(row["id"], row["provenance"]["provider"]) for row in episodes] == [
        (str(bangumi), "bangumi")
    ]

    await fetch(
        session,
        "UPDATE provider SET redistribution_policy='forbidden' WHERE slug='bangumi' RETURNING id",
        {},
    )
    count, episodes = await episode_page(session, cluster=ids, language="", page=1, page_size=10)
    assert count == 1
    assert [(row["id"], row["provenance"]["provider"]) for row in episodes] == [
        (str(anilist), "anilist")
    ]
