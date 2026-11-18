from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from api.contexts.knowledge import enrichment, normalization, web_evidence
from api.contexts.knowledge.enrichment_models import CompletionInput
from api.contexts.presentation.fragments import fetch
from tests.test_normalization_transactions import normalization_runtime as normalization_runtime

TITLE = {
    "field": "title",
    "language": "zh",
    "script": "Hans",
    "text": "标题",
    "kind": "translated",
    "confidence": 0.99,
    "reason": "Source-supported title",
    "source": "model",
}
DESCRIPTION = {**TITLE, "field": "description", "text": "作品简介"}
OUTPUT = {
    "strategy": "complete",
    "proposals": [TITLE, DESCRIPTION],
    "summary": "Metadata proposals",
}


@pytest.fixture
async def enrichment_runtime(normalization_runtime, monkeypatch):
    session, context, _ = normalization_runtime
    monkeypatch.setattr(enrichment, "session_scope", normalization.session_scope)
    gather = AsyncMock(return_value=[])
    monkeypatch.setattr(web_evidence, "gather", gather)
    model = AsyncMock(
        return_value=(OUTPUT, {"input_tokens": 10, "output_tokens": 8, "cost": "0.01"})
    )
    monkeypatch.setattr(enrichment, "complete_json", model)
    return session, context, model, gather


def value(context, **overrides):
    return CompletionInput(
        **{
            "entity_id": str(context.entity_id),
            "provider": "bangumi",
            "external_id": "1",
            "preferred_name": "Anime",
            "missing_fields": ["title:zh", "description:zh"],
            **overrides,
        }
    )


@pytest.mark.asyncio
async def test_default_shadow_pass_keeps_both_fields_reviewable(enrichment_runtime):
    session, context, model, gather = enrichment_runtime
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id
    )
    assert result == {"claims": 2, "applied": 0, "abstained": 0, "strategy": "complete"}
    model.assert_awaited_once()
    gather.assert_awaited_once_with("Anime", entity_id=context.entity_id, run_id=context.run_id)
    assert [row.status for row in await fetch(session, "SELECT status FROM ai_claim", {})] == [
        "proposed",
        "proposed",
    ]
    assert (await fetch(session, "SELECT count(*) AS n FROM claim_evidence", {}))[0].n == 2
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_name", {}))[0].n == 1


@pytest.mark.asyncio
async def test_high_confidence_title_applies_with_source_provenance_and_description_stays_proposed(
    enrichment_runtime,
):
    session, context, _, _ = enrichment_runtime
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
    )
    assert result == {"claims": 2, "applied": 1, "abstained": 0, "strategy": "complete"}
    row = (await fetch(session, "SELECT * FROM entity_name WHERE text='标题'", {}))[0]
    assert (row.language, row.script, row.kind, row.is_machine_generated, row.is_reviewed) == (
        "zh",
        "Hans",
        "translated",
        True,
        False,
    )
    assert row.observation_id == context.observation_id
    assert row.provider_record_id is not None
    claims = await fetch(
        session,
        "SELECT predicate_slug,status,calibrated_confidence FROM ai_claim ORDER BY predicate_slug",
        {},
    )
    assert [(row.predicate_slug, row.status) for row in claims] == [
        ("entity:description", "proposed"),
        ("entity:title", "accepted"),
    ]
    assert [float(row.calibrated_confidence) for row in claims] == [0.891, 0.891]


@pytest.mark.asyncio
async def test_duplicate_title_is_superseded_on_replay(enrichment_runtime):
    session, context, _, _ = enrichment_runtime
    for _ in range(2):
        result = await enrichment.complete(
            value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
        )
    assert result["applied"] == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_name WHERE text='标题'", {}))[
        0
    ].n == 1
    assert (
        await fetch(session, "SELECT count(*) AS n FROM ai_claim WHERE status='superseded'", {})
    )[0].n == 1


@pytest.mark.asyncio
async def test_web_evidence_calibrates_and_links_cached_artifact(enrichment_runtime):
    session, context, model, gather = enrichment_runtime
    artifact = (
        await fetch(
            session,
            """
        INSERT INTO source_artifact
          (id,kind,source_url,content_hash,mime_type,excerpt,object_key,metadata,license_info,
           fetched_at,created_at)
        VALUES (gen_random_uuid(),'search_result','https://source.test/title',:hash,
                'application/json','Documented title','','{}','',now(),now())
        RETURNING id,source_url,content_hash,excerpt,metadata
    """,
            {"hash": "a" * 64},
        )
    )[0]
    await session.commit()
    gather.return_value = [web_evidence.SearchArtifact(**artifact._mapping)]
    model.return_value = (
        {**OUTPUT, "proposals": [{**TITLE, "source": "web", "confidence": 0.87}]},
        {},
    )
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
    )
    assert result["applied"] == 1
    claim = (
        await fetch(session, "SELECT calibrated_confidence,evidence_strength FROM ai_claim", {})
    )[0]
    assert (float(claim.calibrated_confidence), float(claim.evidence_strength)) == (0.87, 1.0)
    assert (await fetch(session, "SELECT count(*) AS n FROM claim_evidence", {}))[0].n == 2
    payload = model.await_args.kwargs["payload"]
    assert payload["web_evidence"][0]["url"] == artifact.source_url


@pytest.mark.asyncio
async def test_contract_retry_uses_one_inference_audit(enrichment_runtime):
    session, context, model, _ = enrichment_runtime
    model.side_effect = [({"strategy": "invalid"}, {}), (OUTPUT, {"input_tokens": 7})]
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id
    )
    assert result["claims"] == 2
    assert model.await_count == 2
    assert "Your previous response did not match" in model.await_args.kwargs["system"]
    row = (await fetch(session, "SELECT status,input_tokens FROM ai_run", {}))[0]
    assert tuple(row) == ("succeeded", 7)


@pytest.mark.asyncio
async def test_two_failed_contract_attempts_abstain_with_failed_step(enrichment_runtime):
    session, context, model, _ = enrichment_runtime
    model.return_value = ({"strategy": "invalid"}, {})
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id
    )
    assert result == {"claims": 0, "applied": 0, "abstained": 1, "strategy": "abstain"}
    assert model.await_count == 2
    assert (await fetch(session, "SELECT status FROM ai_run", {}))[0].status == "failed"
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0


@pytest.mark.asyncio
async def test_oversized_title_remains_a_reviewable_claim(enrichment_runtime):
    session, context, model, _ = enrichment_runtime
    model.return_value = ({**OUTPUT, "proposals": [{**TITLE, "text": "x" * 600}]}, {})
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
    )
    assert (result["claims"], result["applied"]) == (1, 0)
    assert (await fetch(session, "SELECT status FROM ai_claim", {}))[0].status == "proposed"


@pytest.mark.asyncio
async def test_unknown_language_and_existing_normalized_name_are_filtered(enrichment_runtime):
    session, context, model, _ = enrichment_runtime
    model.return_value = (
        {**OUTPUT, "proposals": [{**TITLE, "language": "fr"}, {**TITLE, "text": " A n i m e "}]},
        {},
    )
    result = await enrichment.complete(
        value(context, existing_names={"en": "Anime"}),
        run_id=context.run_id,
        observation_id=context.observation_id,
        apply=True,
    )
    assert result["claims"] == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0


@pytest.mark.asyncio
async def test_revoked_source_cannot_gain_proposals_or_names(enrichment_runtime):
    session, context, model, _ = enrichment_runtime

    async def revoke(**kwargs):
        await fetch(session, "UPDATE entity_representation SET is_active=false RETURNING id", {})
        await session.commit()
        return OUTPUT, {}

    model.side_effect = revoke
    with pytest.raises(ValueError, match="active source"):
        await enrichment.complete(
            value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"


@pytest.mark.asyncio
async def test_partial_proposal_failure_rolls_back_claims_and_name_application(
    enrichment_runtime,
    monkeypatch,
):
    session, context, _, _ = enrichment_runtime
    original = enrichment.apply_title

    async def fail_on_description(session, **kwargs):
        if kwargs["proposal"].field == "description":
            raise RuntimeError("proposal write failed")
        return await original(session, **kwargs)

    monkeypatch.setattr(enrichment, "apply_title", fail_on_description)
    with pytest.raises(RuntimeError, match="proposal write failed"):
        await enrichment.complete(
            value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
        )
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM entity_name WHERE text='标题'", {}))[
        0
    ].n == 0
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"


@pytest.mark.asyncio
async def test_missing_entity_fails_before_search_or_model(enrichment_runtime):
    _, context, model, gather = enrichment_runtime
    with pytest.raises(LookupError, match="Entity not found"):
        await enrichment.complete(value(context, entity_id=str(uuid4())), run_id=context.run_id)
    model.assert_not_awaited()
    gather.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_names_from_multiple_provenances_remain_unchanged(enrichment_runtime):
    session, context, model, _ = enrichment_runtime
    for observation in [None, context.observation_id]:
        await fetch(
            session,
            """
            INSERT INTO entity_name
              (entity_id,text,language,script,region,kind,is_official,is_original,
               is_machine_generated,is_reviewed,provider_record_id,observation_id,
               created_at,updated_at)
            VALUES (:entity,'标题','zh','Hans','','translated',false,false,false,true,
              (SELECT provider_record_id FROM provider_observation WHERE id=:observation),
              :observation,now(),now()) RETURNING id
            """,
            {"entity": context.entity_id, "observation": observation},
        )
    await session.commit()
    model.return_value = ({**OUTPUT, "proposals": [TITLE]}, {})
    result = await enrichment.complete(
        value(context), run_id=context.run_id, observation_id=context.observation_id, apply=True
    )
    assert (result["claims"], result["applied"]) == (1, 0)
    assert (await fetch(session, "SELECT status FROM ai_claim", {}))[0].status == "superseded"
    rows = await fetch(session, "SELECT is_reviewed FROM entity_name WHERE text='标题'", {})
    assert len(rows) == 2 and all(row.is_reviewed for row in rows)
