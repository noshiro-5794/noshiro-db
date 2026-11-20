from datetime import UTC, datetime

import pytest

from api.contexts.presentation.fragments import fetch
from api.worker.records import ensure_record, record_payload


@pytest.mark.asyncio
async def test_embedded_reference_preserves_full_payload_and_promotes_stub(vndb_session):
    session = vndb_session
    parameters = {
        "provider_slug": "vndb",
        "namespace_slug": "vn",
        "resource_type": "subject",
        "external_id": "v1",
    }
    identifier = await ensure_record(session, **parameters, canonical_url="https://vndb.org/v1")
    stub = (await fetch(session, "SELECT * FROM provider_record WHERE id=:id", {"id": identifier}))[
        0
    ]
    assert stub.raw_state == "stub"
    assert stub.latest_revision_id is None
    written = await record_payload(
        session,
        **parameters,
        payload={"id": "v1", "title": "A visual novel"},
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert written.record_id == identifier
    assert written.changed
    await fetch(
        session,
        "UPDATE provider_record SET status='missing' WHERE id=:id RETURNING id",
        {"id": identifier},
    )
    assert await ensure_record(session, **parameters) == identifier
    full = (await fetch(session, "SELECT * FROM provider_record WHERE id=:id", {"id": identifier}))[
        0
    ]
    assert full.status == "active"
    assert full.raw_state == "raw"
    assert full.latest_revision_id == written.revision_id
    assert full.latest_payload_hash
    assert full.canonical_url == "https://vndb.org/v1"
    assert full.first_seen_at == stub.first_seen_at
    repeated = await record_payload(
        session, **parameters, payload={"title": "A visual novel", "id": "v1"}
    )
    assert not repeated.changed
    assert repeated.revision_id == written.revision_id
    assert (await fetch(session, "SELECT count(*) AS n FROM provider_revision", {}))[0].n == 1
