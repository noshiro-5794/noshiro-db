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
    assert await metadata_harness.submit_draft(session, draft) == saved
    alternative = draft.model_copy(update={"description": "Updated synopsis."})
    next_revision = await metadata_harness.submit_draft(session, alternative)
    assert next_revision["id"] != saved["id"]
    assert (
        await activate(session, entity_id=entity_id, language="en", revision_id=saved["id"])
        == saved["id"]
    )

    async def descriptions():
        document = await entity_detail(
            session, root=entity_id, cluster_ids=[str(entity_id)], language="en"
        )
        return [row["text"] for row in document["descriptions"]]

    assert await descriptions() == ["Published synopsis.", "Original description."]
    assert await activate(session, entity_id=entity_id, language="en", revision_id=0) is None
    assert (await descriptions())[0] == "Published synopsis."

    assert (await descriptions())[0] == "Published synopsis."
    assert (
        await activate(session, entity_id=entity_id, language="en", revision_id=next_revision["id"])
        == (next_revision["id"])
    )
    assert (await descriptions())[0] == "Updated synopsis."
    await fetch(
        session,
        "UPDATE entity_description SET text='New source wording.' WHERE id=:id RETURNING id",
        {"id": draft.description_source_ids[0]},
    )
    assert await descriptions() == ["New source wording."]

    await fetch(
        session,
        "UPDATE provider SET ai_usage_policy='forbidden' WHERE slug='bangumi' RETURNING id",
        {},
    )
    assert await descriptions() == ["New source wording."]
    with pytest.raises(ValueError, match="evidence has changed"):
        await metadata_harness.submit_draft(session, draft)


@pytest.mark.asyncio
async def test_extended_fields_select_source_evidence_without_rewriting_credits(
    bangumi_session, register_provider
):
    from api.contexts.index.resolution import merge
    from api.contexts.presentation.work_fields import FieldChoice
    from api.worker.mal_import import import_anime

    session = bangumi_session
    await register_provider("mal", "MyAnimeList")
    native = "葬送のフリーレン 第2期"
    credit = "北川朋哉(29-30,38)\uff1b黄金乡篇部分\uff1a北川朋哉(38)"
    root = await import_subject(
        session,
        {
            "id": 515759,
            "type": 2,
            "name": native,
            "name_cn": "葬送的芙莉莲 第二季",
            "summary": "继续踏上旅程。",
            "infobox": [
                {"key": "分镜", "value": credit},
                {"key": "评分", "value": "9.1"},
                {"key": "备注", "value": "不明"},
            ],
        },
    )
    other = await import_anime(
        session,
        {
            "id": 59978,
            "title": "Frieren Season 2",
            "media_type": "tv",
            "broadcast": {"day_of_the_week": "friday", "start_time": "23:00"},
            "genres": [{"id": 10, "name": "Fantasy"}],
        },
    )
    await merge(session, source_id=other, target_id=root, method="rule", reason="same season")
    await fetch(session, "UPDATE provider SET ai_usage_policy='allowed' RETURNING id", {})
    evidence = await metadata_harness.evidence(session, entity_id=root, language="zh-Hans")
    bundle = evidence["bundle"]
    candidates = {item["key"]: item for item in bundle["fields"]}
    assert candidates["infobox:分镜"]["values"] == [credit]
    assert candidates["broadcast-time"]["provider"] == "mal"
    assert not any(item["label"] in {"评分", "备注"} for item in candidates.values())
    draft = metadata_harness.MetadataDraft(
        entity_id=root,
        language="zh-Hans",
        input_hash=evidence["input_hash"],
        title_name_id=next(row["id"] for row in bundle["names"] if row["language"] == "zh-Hans"),
        description="**芙莉莲**与同伴再度启程。\n\n他们仍在路上。",
        description_source_ids=[bundle["descriptions"][0]["id"]],
        fields=[
            FieldChoice(evidence_id=candidates["infobox:分镜"]["id"], label="分镜"),
            FieldChoice(evidence_id=candidates["broadcast-time"]["id"], label="播出时间"),
        ],
    )
    saved = await metadata_harness.submit_draft(session, draft)
    assert await activate(session, entity_id=root, language="zh-Hans", revision_id=saved["id"])
    result = await entity_detail(
        session, root=root, cluster_ids=[str(root), str(other)], language="zh-CN"
    )
    assert result["original_title"]["text"] == native
    assert result["original_title"]["language"] == "ja"
    assert result["descriptions"][0]["text"] == draft.description
    assert result["display_fields"][0]["values"] == [credit]
    assert result["display_fields"][1]["values"] == ["23:00"]
