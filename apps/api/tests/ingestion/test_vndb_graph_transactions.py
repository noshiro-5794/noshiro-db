from unittest.mock import AsyncMock

import pytest

from api.db import fetch
from api.integrations.providers.vndb import VNDBImportBatch
from api.worker import vndb_graph
from api.worker.vndb_import import project_batch

WORK = {
    "id": "v1",
    "title": "Visual novel",
    "olang": "ja",
    "developers": [{"id": "p1", "name": "Studio", "original": "制作社"}],
    "staff": [{"id": "s1", "aid": 10, "name": "Writer", "lang": "ja", "role": "scenario"}],
    "relations": [{"id": "v2", "title": "Sequel", "relation": "seq", "relation_official": True}],
    "va": [
        {
            "staff": {"id": "s1", "aid": 10, "name": "Writer", "lang": "ja"},
            "character": {"id": "c1", "name": "Heroine"},
        }
    ],
}
RELEASES = (
    {
        "id": "r1",
        "title": "Edition",
        "released": "2024-02",
        "platforms": ["win"],
        "minage": 18,
        "official": True,
        "patch": False,
        "freeware": False,
        "resolution": "1920x1080",
        "vns": [{"id": "v1", "rtype": "complete"}],
        "producers": [{"id": "p1", "name": "Studio", "developer": True, "publisher": True}],
    },
)
CHARACTERS = (
    {
        "id": "c1",
        "name": "Heroine",
        "original": "主人公",
        "description": "Character biography",
        "image": {"url": "https://provider.test/character.jpg", "sexual": 0},
        "sex": ["f", "f"],
        "age": 20,
        "vns": [{"id": "v1", "role": "main", "spoiler": 1}],
        "traits": [
            {
                "id": "i1",
                "name": "Trait",
                "group_id": "i2",
                "group_name": "Group",
                "spoiler": 2,
                "lie": True,
            }
        ],
    },
)
CONTRIBUTORS = (
    {
        "id": "s1",
        "name": "Writer",
        "original": "筆名",
        "description": "Person biography",
        "aliases": [{"aid": 10, "name": "Writer", "latin": "Writer Latin"}],
        "extlinks": [{"url": "https://person.test", "label": "Homepage"}],
    },
)


@pytest.mark.asyncio
async def test_complete_related_graph_is_idempotent_and_voice_uses_current_appearance(vndb_session):
    session = vndb_session
    batch = VNDBImportBatch(WORK, RELEASES, CHARACTERS, CONTRIBUTORS, True)
    projection = await project_batch(session, "v1", batch)
    assert await project_batch(session, "v1", batch) == projection
    counts = {}
    for table in (
        "provider_revision",
        "credit",
        "appearance",
        "voice_performance",
        "release_work",
        "release_work_evidence",
        "entity_relation",
        "entity_relation_evidence",
        "person",
        "organization",
        "content_rating",
    ):
        counts[table] = (await fetch(session, f"SELECT count(*) AS n FROM {table}", {}))[0].n
    assert counts == {
        "provider_revision": 5,
        "credit": 2,
        "appearance": 1,
        "voice_performance": 1,
        "release_work": 1,
        "release_work_evidence": 1,
        "entity_relation": 3,
        "entity_relation_evidence": 3,
        "person": 1,
        "organization": 1,
        "content_rating": 1,
    }
    voices = await fetch(
        session,
        "SELECT a.role, a.spoiler_level, v.language, v.credited_as"
        " FROM voice_performance v"
        " JOIN appearance a ON a.id=v.appearance_id",
        {},
    )
    assert tuple(voices[0]) == ("main", 1, "ja", "Writer")
    alias = await fetch(
        session,
        "SELECT r.mapping_kind"
        " FROM entity_representation r"
        " JOIN provider_record p ON p.id=r.provider_record_id"
        " JOIN provider_namespace n ON n.id=p.namespace_id"
        " WHERE n.slug='staff-alias'",
        {},
    )
    assert [row.mapping_kind for row in alias] == ["variant"]
    traits = await fetch(
        session,
        "SELECT p.slug, f.value, e.json_pointer, f.spoiler_level"
        " FROM fact f"
        " JOIN predicate p ON p.id=f.predicate_id"
        " JOIN fact_evidence e ON e.fact_id=f.id"
        " WHERE p.slug='vndb-trait-lie'",
        {},
    )
    assert tuple(traits[0]) == (
        "vndb-trait-lie",
        {"trait_id": "i1", "lie": True},
        "/traits/0/lie",
        2,
    )


@pytest.mark.asyncio
async def test_projection_failure_rolls_back_every_record_but_keeps_callers_transaction(
    vndb_session, monkeypatch
):
    session = vndb_session
    monkeypatch.setattr(
        vndb_graph, "import_voices", AsyncMock(side_effect=ValueError("invalid voice"))
    )
    with pytest.raises(ValueError, match="invalid voice"):
        await project_batch(
            session, "v1", VNDBImportBatch(WORK, RELEASES, CHARACTERS, CONTRIBUTORS, True)
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM entity", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_record", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM provider WHERE slug='vndb'", {}))[
        0
    ].n == 1


@pytest.mark.asyncio
async def test_work_only_batch_still_imports_embedded_credits_relations_and_voices(vndb_session):
    session = vndb_session
    await project_batch(session, "v1", VNDBImportBatch(work=WORK))
    assert (await fetch(session, "SELECT count(*) AS n FROM credit", {}))[0].n == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_relation", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM voice_performance", {}))[0].n == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1


@pytest.mark.asyncio
async def test_release_pointer_identifies_original_array_position(vndb_session):
    session = vndb_session
    release = {
        **RELEASES[0],
        "vns": [{"id": "v99", "rtype": "trial"}, {"id": "v1", "rtype": "partial"}],
    }
    await project_batch(
        session, "v1", VNDBImportBatch(work=WORK, releases=(release,), related_fetched=True)
    )
    evidence = await fetch(
        session,
        "SELECT e.json_pointer, e.raw_role, r.role"
        " FROM release_work_evidence e"
        " JOIN release_work r ON r.id=e.release_work_id",
        {},
    )
    assert tuple(evidence[0]) == ("/releases/0/vns/1", "partial", "included")
