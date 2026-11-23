import pytest

from api.contexts.presentation import metadata_harness
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.display import activate
from api.db import fetch
from api.worker.subject_import import import_subject


@pytest.mark.asyncio
async def test_model_draft_is_work_scoped_and_reads_through_publication(bangumi_session):
    session = bangumi_session
    entity_id = await import_subject(
        session, {"id": 1, "type": 2, "name": "Work", "summary": "Original description."}
    )
    await fetch(
        session,
        "UPDATE provider SET ai_usage_policy='allowed' WHERE slug='bangumi' RETURNING id",
        {},
    )
    input = await metadata_harness.evidence(session, entity_id=entity_id, language="en")
    bundle = input["bundle"]
    assert {"credits", "relations", "episodes"}.isdisjoint(bundle)
    draft = metadata_harness.MetadataDraft(
        entity_id=entity_id,
        language="en",
        input_hash=input["input_hash"],
        title_name_id=bundle["names"][0]["id"],
        description="Published synopsis.",
        description_source_ids=[bundle["descriptions"][0]["id"]],
    )
    saved = await metadata_harness.submit_draft(session, draft)
    assert saved["state"] == "draft"
    assert (
        await activate(session, entity_id=entity_id, language="en", input_hash=draft.input_hash)
        == saved["id"]
    )

    async def descriptions():
        document = await entity_detail(
            session, root=entity_id, cluster_ids=[str(entity_id)], language="en"
        )
        return [row["text"] for row in document["descriptions"]]

    assert await descriptions() == ["Published synopsis.", "Original description."]
    assert await activate(session, entity_id=entity_id, language="en", input_hash="0" * 64) is None
    assert (await descriptions())[0] == "Published synopsis."

    await fetch(
        session,
        "UPDATE provider SET ai_usage_policy='forbidden' WHERE slug='bangumi' RETURNING id",
        {},
    )
    assert await descriptions() == ["Original description."]
    with pytest.raises(ValueError, match="evidence has changed"):
        await metadata_harness.submit_draft(session, draft)
