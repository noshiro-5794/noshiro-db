from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from api.contexts.knowledge import normalization
from api.contexts.knowledge.agent_runs import EvidenceContext
from api.db import fetch
from api.shared import inference
from api.worker.subject_import import import_subject

OUTPUT = {
    "action": "map_existing",
    "normalized_key": "sf",
    "preferred_term": "Science fiction",
    "language": "en",
    "confidence": 0.95,
    "reason": "Explicit genre abbreviation.",
    "existing_term_slug": "science-fiction",
}


@pytest.fixture
async def normalization_runtime(bangumi_session, monkeypatch):
    session = bangumi_session
    entity = await import_subject(session, {"id": 1, "name": "Anime", "type": 2})
    observation = (
        await fetch(
            session, "SELECT id FROM provider_observation ORDER BY observed_at DESC LIMIT 1", {}
        )
    )[0].id
    run = (
        await fetch(
            session,
            """
        INSERT INTO agent_run
          (id,kind,status,title,idempotency_key,idempotency_scope,trace_id,metadata,checkpoint,
           budget,error,created_at,updated_at)
        VALUES (gen_random_uuid(),'admin_sync','queued','Fixture','','','','{}','{}','{}','',
                now(),now()) RETURNING id
        """,
            {},
        )
    )[0].id
    await session.commit()

    @asynccontextmanager
    async def scope():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(normalization, "session_scope", scope)
    monkeypatch.setattr(inference, "session_scope", scope)
    model = AsyncMock(
        return_value=(OUTPUT, {"input_tokens": 10, "output_tokens": 8, "cost": "0.01"})
    )
    monkeypatch.setattr(normalization, "complete_json", model)
    return session, EvidenceContext(entity, run, observation_id=observation), model


def value(**overrides):
    return normalization.NormalizationInput(
        **{
            "vocabulary": "provider-tag",
            "source_text": "SF",
            "provider_namespace": "subject",
            **overrides,
        }
    )


@pytest.mark.asyncio
async def test_model_normalization_persists_linked_step_inference_claim_and_evidence(
    normalization_runtime,
):
    session, context, model = normalization_runtime
    result = await normalization.normalize(value(), evidence=context)
    assert result.source == "model"
    assert result.existing_term_slug == "science-fiction"
    model.assert_awaited_once()
    rows = await fetch(
        session,
        """
        SELECT s.sequence,s.status,r.status AS inference_status,r.input_tokens,r.output_tokens,
          c.predicate_slug,c.status AS claim_status,c.evidence_strength,e.observation_id,e.excerpt
        FROM agent_step s JOIN ai_run r ON r.agent_step_id=s.id
        JOIN ai_claim c ON c.step_id=s.id JOIN claim_evidence e ON e.claim_id=c.id
    """,
        {},
    )
    row = rows[0]
    assert (row.sequence, row.status, row.inference_status) == (0, "succeeded", "succeeded")
    assert (row.input_tokens, row.output_tokens) == (10, 8)
    assert (row.predicate_slug, row.claim_status, row.evidence_strength) == (
        "taxonomy:provider-tag",
        "proposed",
        0,
    )
    assert (row.observation_id, row.excerpt) == (context.observation_id, "SF")
    assert (await fetch(session, "SELECT count(*) AS n FROM taxonomy_term", {}))[0].n == 0


@pytest.mark.asyncio
async def test_reviewed_namespace_alias_bypasses_model_and_keeps_evidence(normalization_runtime):
    session, context, model = normalization_runtime
    taxonomy = (
        await fetch(
            session,
            "INSERT INTO taxonomy (slug,name,description) VALUES ('genre','Genre','') RETURNING id",
            {},
        )
    )[0].id
    term = (
        await fetch(
            session,
            "INSERT INTO taxonomy_term (slug,taxonomy_id) "
            "VALUES ('science-fiction',:id) RETURNING id",
            {"id": taxonomy},
        )
    )[0].id
    namespace = (
        await fetch(session, "SELECT id FROM provider_namespace WHERE slug='subject'", {})
    )[0].id
    for ns, reviewed, preferred, language in [
        (None, True, "Global", "en"),
        (namespace, False, "Unreviewed", ""),
        (namespace, True, "Science fiction", "en"),
    ]:
        await fetch(
            session,
            """
            INSERT INTO taxonomy_alias
              (vocabulary,provider_namespace_id,source_text,normalized_key,preferred_term,
               language,script,confidence,is_reviewed,origin,term_id,created_at,updated_at)
            VALUES ('provider-tag',:namespace,'SF','sf',:preferred,:language,'Latn',0.99,:reviewed,
                    'manual',:term,now(),now()) RETURNING id
        """,
            {
                "namespace": ns,
                "reviewed": reviewed,
                "preferred": preferred,
                "term": term,
                "language": language,
            },
        )
    await session.commit()
    result = await normalization.normalize(value(), evidence=context)
    assert (result.source, result.preferred_term, result.script) == (
        "alias",
        "Science fiction",
        "Latn",
    )
    model.assert_not_awaited()
    assert (await fetch(session, "SELECT evidence_strength FROM ai_claim", {}))[
        0
    ].evidence_strength == 1
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_run", {}))[0].n == 0


@pytest.mark.asyncio
async def test_invalid_model_contract_preserves_raw_and_failed_audit(normalization_runtime):
    session, context, model = normalization_runtime
    model.return_value = ({"action": "invalid"}, {})
    result = await normalization.normalize(value(), evidence=context)
    assert (result.source, result.action, result.preferred_term) == ("raw", "preserve_raw", "SF")
    assert (await fetch(session, "SELECT status FROM ai_run", {}))[0].status == "failed"
    step = (await fetch(session, "SELECT status,output,error FROM agent_step", {}))[0]
    assert step.status == "failed"
    assert step.output["source"] == "raw"
    assert step.error
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 1


@pytest.mark.asyncio
async def test_unstable_map_existing_proposal_requires_new_term_review(normalization_runtime):
    session, context, model = normalization_runtime
    model.return_value = ({**OUTPUT, "existing_term_slug": ""}, {})
    result = await normalization.normalize(value(), evidence=context)
    assert result.action == "propose_new"
    assert (await fetch(session, "SELECT proposed_value FROM ai_claim", {}))[0].proposed_value[
        "action"
    ] == "propose_new"


@pytest.mark.asyncio
async def test_inactive_source_is_rejected_before_model_or_step_creation(normalization_runtime):
    session, context, model = normalization_runtime
    await fetch(session, "UPDATE entity_representation SET is_active=false RETURNING id", {})
    await session.commit()
    with pytest.raises(ValueError, match="active source"):
        await normalization.normalize(value(), evidence=context)
    model.assert_not_awaited()
    assert (await fetch(session, "SELECT count(*) AS n FROM agent_step", {}))[0].n == 0


@pytest.mark.asyncio
async def test_standalone_normalization_has_no_agent_or_inference_side_effects(
    normalization_runtime,
):
    session, _, model = normalization_runtime
    result = await normalization.normalize(value())
    assert result.source == "model"
    model.assert_awaited_once()
    for table in ["ai_run", "ai_claim", "agent_step"]:
        assert (await fetch(session, f"SELECT count(*) AS n FROM {table}", {}))[0].n == 0


@pytest.mark.asyncio
async def test_source_deactivated_during_inference_cannot_gain_claim(normalization_runtime):
    session, context, model = normalization_runtime

    async def revoke_source(**kwargs):
        await fetch(session, "UPDATE entity_representation SET is_active=false RETURNING id", {})
        await session.commit()
        return OUTPUT, {}

    model.side_effect = revoke_source
    with pytest.raises(ValueError, match="active source"):
        await normalization.normalize(value(), evidence=context)
    assert (await fetch(session, "SELECT count(*) AS n FROM ai_claim", {}))[0].n == 0
    assert (await fetch(session, "SELECT status FROM ai_run", {}))[0].status == "succeeded"
    assert (await fetch(session, "SELECT status FROM agent_step", {}))[0].status == "failed"


@pytest.mark.asyncio
async def test_missing_artifact_is_rejected_before_model(normalization_runtime):
    _, context, model = normalization_runtime
    artifact_context = replace(context, observation_id=None, artifact_id=context.run_id)
    with pytest.raises(ValueError, match="Artifact"):
        await normalization.normalize(value(), evidence=artifact_context)
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_source_persists_exactly_one_evidence_link(normalization_runtime):
    session, context, model = normalization_runtime
    artifact = (
        await fetch(
            session,
            """
        INSERT INTO source_artifact
          (id,kind,source_url,content_hash,mime_type,excerpt,object_key,metadata,license_info,
           fetched_at,created_at)
        VALUES (gen_random_uuid(),'search_result','https://source.test/genre',:hash,
                'application/json','Science fiction','','{}','',now(),now()) RETURNING id
        """,
            {"hash": "a" * 64},
        )
    )[0].id
    await session.commit()
    result = await normalization.normalize(
        value(), evidence=replace(context, observation_id=None, artifact_id=artifact)
    )
    assert result.source == "model"
    model.assert_awaited_once()
    evidence = (await fetch(session, "SELECT observation_id,artifact_id FROM claim_evidence", {}))[
        0
    ]
    assert evidence.observation_id is None
    assert evidence.artifact_id == artifact
