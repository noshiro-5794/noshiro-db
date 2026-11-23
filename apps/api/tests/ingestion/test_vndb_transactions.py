from decimal import Decimal

import pytest

from api.db import fetch
from api.worker.vndb_projection import project_work


@pytest.mark.asyncio
async def test_work_projection_preserves_source_flags_safety_and_revision_metrics(vndb_session):
    session = vndb_session
    data = {
        "id": "v1",
        "title": "Original title",
        "olang": "ja",
        "alttitle": "原題",
        "titles": [{"title": "原題", "lang": "ja", "latin": "Gendai", "official": True}],
        "description": "A description",
        "length_minutes": 0,
        "devstatus": 0,
        "released": "2024-02",
        "languages": ["ja"],
        "length_votes": 0,
        "image": {"url": "https://provider.test/poster.jpg", "sexual": 1.6},
        "screenshots": [{"url": "https://provider.test/screen.jpg", "sexual": 0}],
        "extlinks": [{"url": "https://example.test", "label": "Éditeur Site"}],
        "tags": [{"id": "g1", "name": "Drama", "rating": 2.3, "spoiler": 2}],
        "rating": 80,
        "votecount": 100,
    }
    projection = await project_work(session, "v1", data)
    assert await project_work(session, "v1", data) == projection
    rows = await fetch(
        session,
        "SELECT * FROM entity_name WHERE entity_id=:id ORDER BY id",
        {"id": projection.entity_id},
    )
    assert len(rows) == 3
    assert [(row.text, row.kind, row.is_original, row.is_official) for row in rows] == [
        ("原題", "original", True, True),
        ("Gendai", "romanized", False, False),
        ("Original title", "official", False, True),
    ]
    media = await fetch(
        session,
        "SELECT a.safety, m.purpose, m.sort_order FROM entity_media AS m"
        " JOIN media_asset AS a ON a.id=m.asset_id"
        " WHERE m.entity_id=:id ORDER BY m.purpose",
        {"id": projection.entity_id},
    )
    assert [(row.safety, row.purpose) for row in media] == [
        ("explicit", "poster"),
        ("safe", "screenshot"),
    ]
    assert (
        await fetch(
            session, "SELECT audience FROM entity WHERE id=:id", {"id": projection.entity_id}
        )
    )[0].audience == "adult"
    profile = (
        await fetch(
            session, "SELECT * FROM galgame_profile WHERE work_id=:id", {"id": projection.entity_id}
        )
    )[0]
    assert profile.playtime_minutes == 0
    assert profile.development_status == "finished"
    link = (
        await fetch(
            session,
            "SELECT link_type FROM external_link WHERE entity_id=:id",
            {"id": projection.entity_id},
        )
    )[0]
    assert link.link_type == "editeur-site"
    observed = await fetch(
        session,
        "SELECT metric, value FROM ranking.provider_metric WHERE entity_id=:id ORDER BY metric",
        {"id": projection.entity_id},
    )
    assert [(row.metric, row.value) for row in observed] == [
        ("playtime-votes", Decimal(0)),
        ("score", Decimal(80)),
        ("votes", Decimal(100)),
    ]
    evidence = await fetch(
        session,
        "SELECT json_pointer FROM fact_evidence WHERE observation_id=:id ORDER BY json_pointer",
        {"id": projection.observation_id},
    )
    assert [row.json_pointer for row in evidence] == ["/languages", "/released"]
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1
    tags = await fetch(
        session,
        "SELECT relevance, spoiler_level FROM entity_term WHERE entity_id=:id",
        {"id": projection.entity_id},
    )
    assert [(row.relevance, row.spoiler_level) for row in tags] == [(Decimal("2.3"), 2)]
    membership = (
        await fetch(
            session,
            "SELECT inclusion_reason FROM curated_membership WHERE entity_id=:id",
            {"id": projection.entity_id},
        )
    )[0]
    assert membership.inclusion_reason == "VNDB visual novel"
    refreshed = await project_work(session, "v1", {"id": "v1"})
    assert refreshed.entity_id == projection.entity_id
    assert refreshed.observation_id != projection.observation_id
    profile = (
        await fetch(
            session, "SELECT * FROM galgame_profile WHERE work_id=:id", {"id": projection.entity_id}
        )
    )[0]
    assert profile.playtime_minutes is None
    assert profile.development_status == ""
    assert (
        await fetch(
            session, "SELECT audience FROM entity WHERE id=:id", {"id": projection.entity_id}
        )
    )[0].audience == "adult"
