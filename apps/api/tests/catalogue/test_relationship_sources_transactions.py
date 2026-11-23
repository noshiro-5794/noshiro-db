from uuid import uuid4

import pytest

from api.contexts.ingestion import entities, facts, observations, records, relations
from api.contexts.presentation.credits import entity_credits
from api.contexts.presentation.episodes import episode_ids, episode_page
from api.db import fetch
from api.worker.subject_import import import_subject


async def _episode(session, work_id, provider: str, *, complete: bool | None = None):
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
        normalized_data={"id": 1, "complete": complete},
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


@pytest.mark.asyncio
async def test_complete_episode_source_owns_the_list_and_its_fields(
    bangumi_session, register_provider
):
    await register_provider("anilist", "AniList")
    session = bangumi_session
    work = await import_subject(session, {"id": 1, "type": 2, "name": "Work"})
    await _episode(session, work, "bangumi", complete=False)
    complete = await _episode(session, work, "anilist", complete=True)
    evidence = await fetch(
        session,
        """
        SELECT provider.slug, observation.id FROM provider_observation AS observation
        JOIN provider_record AS record ON record.id = observation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider ON provider.id = namespace.provider_id
        WHERE observation.schema_name = 'index.episode'
        """,
        {},
    )
    for row in evidence:
        await facts.record_fact(
            session,
            entity_id=complete,
            observation_id=row.id,
            slug="episode-number",
            name="Episode number",
            value=1 if row.slug == "anilist" else 99,
            value_type="number",
            json_pointer="/episode",
        )
    count, episodes = await episode_page(
        session, cluster=[str(work)], language="", page=1, page_size=10
    )
    assert count == 1
    assert [(row["id"], row["number"]) for row in episodes] == [(str(complete), 1)]


@pytest.mark.asyncio
async def test_credit_sources_fall_back_by_normalized_role(bangumi_session, register_provider):
    await register_provider("anilist", "AniList")
    session = bangumi_session
    work = await import_subject(session, {"id": 1, "type": 2, "name": "Work"})
    await _episode(session, work, "bangumi")
    await _episode(session, work, "anilist")
    assignments = await fetch(
        session,
        """
        SELECT provider.slug, observation.id FROM provider_observation AS observation
        JOIN provider_record AS record ON record.id = observation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider ON provider.id = namespace.provider_id
        WHERE observation.schema_name = 'index.episode'
        """,
        {},
    )
    sources = {item.slug: item.id for item in assignments}
    for provider, role in (("bangumi", "导演"), ("anilist", "Director"), ("anilist", "Music")):
        person = uuid4()
        await fetch(
            session,
            """
            INSERT INTO entity (id,kind,lifecycle,visibility,audience,spoiler_level,
                                created_at,updated_at)
            VALUES (:id,'person','active','public','general',0,now(),now()) RETURNING id
            """,
            {"id": person},
        )
        await relations.ensure_contributor(session, person, "person")
        await relations.credit(session, work, person, sources[provider], role=role, credited_as="")
    result = await entity_credits(session, cluster=[str(work)], language="")
    assert [(item["role"], item["provenance"]["provider"]) for item in result] == [
        ("导演", "bangumi"),
        ("Music", "anilist"),
    ]
