import pytest

from api.contexts.index.resolution import ResolutionError, merge, resolve, split
from api.db import fetch
from api.worker.subject_import import import_subject


@pytest.mark.asyncio
async def test_binding_and_split_preserve_source_entity_and_fact_rows(bangumi_session):
    session = bangumi_session
    source = await import_subject(session, {"id": 1, "name": "Imported work", "type": 2, "eps": 12})
    target = await import_subject(session, {"id": 2, "name": "Catalogue work", "type": 2})

    async def data_snapshot():
        return [
            [
                row.data
                for row in await fetch(
                    session, f"SELECT to_jsonb(row) AS data FROM {table} AS row ORDER BY id", {}
                )
            ]
            for table in ("entity", "fact", "provider_revision", "entity_representation")
        ]

    before = await data_snapshot()
    event = await merge(
        session, source_id=source, target_id=target, method="rule", reason="Verified same work."
    )
    assert await resolve(session, source) == target
    assert await data_snapshot() == before
    split_id = await split(session, merge_event_id=event, reason="Corrected identity.")
    assert split_id is not None
    assert await resolve(session, source) == source
    assert await data_snapshot() == before
    with pytest.raises(ResolutionError, match="already inactive"):
        await split(session, merge_event_id=event, reason="Repeated request.")
