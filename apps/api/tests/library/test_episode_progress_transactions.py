from uuid import UUID, uuid4

import pytest

from api.contexts.library import progress
from api.db import fetch
from tests.library.test_library_resources_transactions import library_client as library_client


@pytest.fixture
async def progress_client(library_client):
    session, client, data = library_client
    episodes = [UUID(int=9000 + index) for index in range(5)]
    for index, identifier in enumerate(episodes):
        await fetch(
            session,
            "INSERT INTO entity(id,kind,lifecycle,visibility,audience,spoiler_level,"
            "created_at,updated_at) "
            "VALUES (:id,'episode',:lifecycle,:visibility,'general',0,now(),now()) RETURNING id",
            {
                "id": identifier,
                "lifecycle": "retired" if index == 2 else "active",
                "visibility": "private" if index == 1 else "public",
            },
        )
        if index < 4:
            await fetch(
                session,
                "INSERT INTO entity_relation(from_entity_id,to_entity_id,relation_type,"
                "qualifiers,created_at,updated_at) "
                "VALUES (:work,:episode,'has-episode','{}',now(),now()) RETURNING id",
                {"work": data.entities[0 if index < 3 else 1], "episode": identifier},
            )
    await session.commit()
    yield session, client, data, episodes


@pytest.mark.asyncio
async def test_progress_read_replace_mark_and_remove_are_consistent(progress_client):
    session, client, data, episodes = progress_client
    path = f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/progress/"
    initial = await client.get(path)
    assert initial.status_code == 200, initial.text
    assert initial.json()["total_episodes"] == 2
    assert [item["id"] for item in initial.json()["episodes"]] == [
        str(value) for value in episodes[:2]
    ]
    assert initial.json()["episodes"][0]["number"] is None
    assert initial.json()["finished_count"] == 0
    replaced = await client.put(
        path, json={"finished_episode_ids": [str(episodes[1]), str(episodes[0]), str(episodes[1])]}
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["finished_episode_ids"] == [str(value) for value in episodes[:2]]
    assert (await fetch(session, "SELECT count(*) AS n FROM user_episode_progress", {}))[0].n == 2
    item = f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/{episodes[0]}/progress/"
    for _ in range(2):
        assert (await client.delete(item)).status_code == 204
    for _ in range(2):
        marked = await client.put(item)
        assert marked.status_code == 200 and marked.json()["finished_count"] == 2
    cleared = await client.put(path, json={"finished_episode_ids": []})
    assert cleared.status_code == 200 and cleared.json()["finished_count"] == 0


@pytest.mark.asyncio
async def test_work_membership_checks_preserve_progress_on_failure(progress_client):
    _, client, data, episodes = progress_client
    base = f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/"
    await client.put(f"{base}{episodes[0]}/progress/")
    replaced = await client.put(
        base + "progress/", json={"finished_episode_ids": [str(episodes[4])]}
    )
    assert replaced.status_code == 400
    assert replaced.json()["errors"] == {
        "finished_episode_ids": "Contains an episode outside this Work."
    }
    assert (await client.get(base + "progress/")).json()["finished_count"] == 1
    assert (await client.put(f"{base}{episodes[4]}/progress/")).status_code == 404
    assert (await client.delete(f"{base}{episodes[4]}/progress/")).status_code == 204
    client.headers["x-test-user"] = str(data.other)
    assert (await client.get(base + "progress/")).status_code == 404
    assert (await client.put(f"{base}{episodes[0]}/progress/")).status_code == 404
    assert (await client.delete(f"{base}{episodes[0]}/progress/")).status_code == 404


@pytest.mark.asyncio
async def test_merged_work_relations_and_stored_finished_rows_are_preserved(progress_client):
    session, client, data, episodes = progress_client
    event = uuid4()
    await fetch(
        session,
        "INSERT INTO entity_merge_event(id,source_entity_id,target_entity_id,method,reason,"
        "snapshot,created_at,updated_at) VALUES (:id,:source,:target,'manual','','{}',now(),now())"
        " RETURNING id",
        {"id": event, "source": data.entities[1], "target": data.entities[0]},
    )
    await fetch(
        session,
        "INSERT INTO entity_redirect(source_entity_id,target_entity_id,merge_event_id,"
        "is_active,created_at,updated_at) VALUES (:source,:target,:event,true,now(),now())"
        " RETURNING id",
        {"source": data.entities[1], "target": data.entities[0], "event": event},
    )
    for identifier in [episodes[0], episodes[4], None]:
        await fetch(
            session,
            "INSERT INTO user_episode_progress(user_subject_id,episode_entity_id,is_finished) "
            "VALUES (:entry,:episode,true) RETURNING id",
            {"entry": data.entries[1], "episode": identifier},
        )
    response = await client.get(
        f"/api/v1/users/me/library/entries/{data.entries[1]}/episodes/progress/"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entity_id"] == str(data.entities[0]) and body["total_episodes"] == 3
    assert body["finished_count"] == 3 and body["finished_episode_ids"] == [str(episodes[0])]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,errors",
    [
        ({}, {"finished_episode_ids": ["This field is required."]}),
        ({"finished_episode_ids": None}, {"finished_episode_ids": ["This field may not be null."]}),
        (
            {"finished_episode_ids": "invalid"},
            {"finished_episode_ids": ['Expected a list of items but got type "str".']},
        ),
        (
            {"finished_episode_ids": ["invalid"]},
            {"finished_episode_ids": {"0": ["Must be a valid UUID."]}},
        ),
        (
            {"finished_episode_ids": [None]},
            {"finished_episode_ids": {"0": ["This field may not be null."]}},
        ),
    ],
)
async def test_progress_input_errors_preserve_the_nested_contract(progress_client, body, errors):
    _, client, data, _ = progress_client
    response = await client.put(
        f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/progress/",
        json=body,
    )
    assert response.status_code == 400, response.text
    assert response.json()["errors"] == errors


@pytest.mark.asyncio
async def test_progress_replacement_is_bounded_before_deduplication(progress_client):
    _, client, data, episodes = progress_client
    response = await client.put(
        f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/progress/",
        json={"finished_episode_ids": [str(episodes[0])] * 5001},
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "finished_episode_ids": ["Ensure this field has no more than 5000 elements."]
    }


@pytest.mark.asyncio
async def test_failed_replacement_insert_rolls_back_cleared_progress(progress_client, monkeypatch):
    session, client, data, episodes = progress_client
    base = f"/api/v1/users/me/library/entries/{data.entries[0]}/episodes/"
    assert (await client.put(f"{base}{episodes[0]}/progress/")).status_code == 200
    real_fetch = progress.fetch

    async def fail_insert(session, query, parameters):
        if query.startswith("INSERT INTO user_episode_progress"):
            raise RuntimeError("insert failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(progress, "fetch", fail_insert)
    with pytest.raises(RuntimeError, match="insert failed"):
        await client.put(base + "progress/", json={"finished_episode_ids": [str(episodes[1])]})
    rows = await fetch(session, "SELECT episode_entity_id FROM user_episode_progress", {})
    assert [row.episode_entity_id for row in rows] == [episodes[0]]
