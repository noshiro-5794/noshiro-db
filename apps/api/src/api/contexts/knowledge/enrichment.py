"""Multilingual metadata completion with durable proposals and calibrated title writes."""

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.knowledge import agent_runs, web_evidence
from api.contexts.knowledge.agent_runs import EvidenceContext, WriteGuard
from api.contexts.knowledge.enrichment_models import (
    CompletionInput,
    CompletionResult,
    FieldProposal,
)
from api.contexts.knowledge.web_evidence import SearchArtifact
from api.contexts.presentation.fragments import fetch
from api.shared.ai import complete_json
from api.shared.inference import fail_run, finish_run, start_run
from api.worker.session import session_scope

SYSTEM_PROMPT = """You complete missing multilingual metadata for an ACG entity.
Use only the supplied entity facts and web evidence. Never invent a title or
description without support; prefer abstain when uncertain. Titles must be
verbatim from evidence when available.

Respond with ONLY a JSON object of the form:
{"strategy": "complete", "proposals": [
  {"field": "title", "language": "zh", "script": "", "text": "译名",
   "kind": "translated", "confidence": 0.9,
   "reason": "short evidence citation", "source": "model"}
], "summary": "one sentence"}
Choose "abstain" with an empty proposals list when evidence is insufficient.
"""


def schema_prompt() -> str:
    return (
        SYSTEM_PROMPT
        + "\nOutput must validate against this JSON schema:\n"
        + json.dumps(CompletionResult.model_json_schema(), ensure_ascii=False)
    )


def normalized_text(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", value.strip().lower())


def acceptable(proposal: FieldProposal, value: CompletionInput) -> bool:
    languages = {field.split(":", 1)[-1] for field in value.missing_fields}
    if languages and proposal.language not in languages:
        return False
    normalized = normalized_text(proposal.text)
    return bool(normalized) and all(
        normalized_text(existing) != normalized for existing in value.existing_names.values()
    )


async def model_result(
    value: CompletionInput, step_id: UUID, artifacts: list[SearchArtifact]
) -> tuple[CompletionResult, bool]:
    payload = {
        **value.model_dump(mode="json"),
        "web_evidence": [
            {
                "title": artifact.metadata.get("title", ""),
                "url": artifact.source_url,
                "content": artifact.excerpt[:700],
            }
            for artifact in artifacts
        ],
    }
    run_id = await start_run(
        payload=payload,
        use_case="info_completion",
        prompt_version="info-completion-v1",
        metadata={"skill": "info_completion"},
        agent_step_id=step_id,
    )
    try:
        output, usage = await complete_json(system=schema_prompt(), payload=payload)
        result = CompletionResult.model_validate(output)
    except Exception as first_error:
        retry_prompt = schema_prompt() + "\nYour previous response did not match. Return exactly:\n"
        retry_prompt += (
            json.dumps(
                {
                    "strategy": "complete",
                    "proposals": [],
                    "summary": "Retry with schema-compliant output.",
                },
                ensure_ascii=False,
            )
            + "\nwith your real proposals filled in."
        )
        try:
            output, usage = await complete_json(system=retry_prompt, payload=payload)
            result = CompletionResult.model_validate(output)
        except Exception:
            await fail_run(run_id, first_error)
            return CompletionResult(
                strategy="abstain", summary="Model output did not match the enrichment contract."
            ), True
    await finish_run(run_id, result.model_dump(mode="json"), usage)
    return result, False


async def apply_title(
    session: AsyncSession,
    *,
    proposal: FieldProposal,
    entity_id: UUID,
    claim_id: UUID,
    observation_id: UUID | None,
    apply: bool,
    min_confidence: float,
    calibrated: float,
) -> bool:
    text = proposal.text.strip()
    if proposal.field != "title" or not (apply and calibrated >= min_confidence):
        return False
    # Descriptions and oversized values retain their full reviewable proposal payload.
    if len(text) > 512 or len(proposal.script) > 4:
        return False
    existing = await fetch(
        session,
        "SELECT id FROM entity_name WHERE entity_id=:entity AND text=:text "
        "AND language=:language AND kind=:kind LIMIT 1",
        {"entity": entity_id, "text": text, "language": proposal.language, "kind": proposal.kind},
    )
    if existing:
        await fetch(
            session,
            "UPDATE ai_claim SET status='superseded',policy_decision='duplicate_name',"
            "policy_reason='An identical entity name already exists.',decided_at=now() "
            "WHERE id=:id RETURNING id",
            {"id": claim_id},
        )
        return False
    await fetch(
        session,
        """
        INSERT INTO entity_name
          (entity_id,text,language,script,region,kind,is_official,is_original,
           is_machine_generated,is_reviewed,provider_record_id,observation_id,created_at,updated_at)
        VALUES (:entity,:text,:language,:script,'',:kind,:official,false,true,false,
          (SELECT provider_record_id FROM provider_observation WHERE id=:observation),
          :observation,now(),now()) RETURNING id
        """,
        {
            "entity": entity_id,
            "text": text,
            "language": proposal.language,
            "script": proposal.script,
            "kind": proposal.kind,
            "official": proposal.kind == "official",
            "observation": observation_id,
        },
    )
    await fetch(
        session,
        "UPDATE ai_claim SET status='accepted',policy_decision='auto_apply',"
        "policy_reason=:reason,decided_at=now() WHERE id=:id RETURNING id",
        {"id": claim_id, "reason": f"Confidence {calibrated} >= {min_confidence} threshold."},
    )
    return True


async def persist_proposals(
    session: AsyncSession,
    *,
    value: CompletionInput,
    result: CompletionResult,
    step_id: UUID,
    entity_id: UUID,
    artifacts: list[SearchArtifact],
    observation_id: UUID | None,
    apply: bool,
    min_confidence: float,
) -> dict[str, Any]:
    claims = 0
    applied = 0
    for proposal in result.proposals:
        if not acceptable(proposal, value):
            continue
        strength = 1.0 if proposal.source == "web" and artifacts else 0.9
        calibrated = round(proposal.confidence * strength, 4)
        claim_id = await agent_runs.create_claim(
            session,
            step_id=step_id,
            entity_id=entity_id,
            claim_type="info_completion",
            predicate=f"entity:{proposal.field}",
            value=proposal.model_dump(mode="json"),
            confidence=proposal.confidence,
            evidence_strength=strength,
            calibrated_confidence=calibrated,
        )
        if observation_id is not None:
            await agent_runs.add_evidence(
                session,
                claim_id=claim_id,
                observation_id=observation_id,
                locator=f"/{proposal.field}:{proposal.language}",
                excerpt=value.preferred_name,
                excerpt_hash=agent_runs.payload_hash(
                    {
                        "text": value.preferred_name,
                        "language": proposal.language,
                    }
                ),
            )
        if proposal.source == "web":
            for artifact in artifacts:
                await agent_runs.add_evidence(
                    session,
                    claim_id=claim_id,
                    artifact_id=artifact.id,
                    locator=f"artifact:{artifact.content_hash[:16]}",
                    excerpt=artifact.excerpt,
                    excerpt_hash=artifact.content_hash,
                )
        claims += 1
        if await apply_title(
            session,
            proposal=proposal,
            entity_id=entity_id,
            claim_id=claim_id,
            observation_id=observation_id,
            apply=apply,
            min_confidence=min_confidence,
            calibrated=calibrated,
        ):
            applied += 1
    return {"claims": claims, "applied": applied, "abstained": 0, "strategy": "complete"}


async def complete(
    value: CompletionInput,
    *,
    run_id: UUID,
    observation_id: UUID | None = None,
    apply: bool = False,
    min_confidence: float = 0.85,
    before_write: WriteGuard | None = None,
) -> dict[str, Any]:
    entity_id = UUID(value.entity_id)
    context = None
    if observation_id is not None:
        context = EvidenceContext(entity_id, run_id, observation_id=observation_id)
    async with session_scope() as session:
        existing = await fetch(session, "SELECT id FROM entity WHERE id=:id", {"id": entity_id})
        if not existing:
            raise LookupError("Entity not found.")
        if context is not None:
            await agent_runs.validate_evidence(session, context)
    artifacts = await web_evidence.gather(
        value.preferred_name or value.original_name, entity_id=entity_id, run_id=run_id
    )
    async with session_scope() as session:
        step_id = await agent_runs.create_step(
            session, run_id=run_id, skill="info_completion", payload=value.model_dump(mode="json")
        )
    result = None
    try:
        result, failed = await model_result(value, step_id, artifacts)
        async with session_scope() as session:
            if before_write is not None:
                await before_write(session)
            entities = await fetch(
                session, "SELECT id FROM entity WHERE id=:id FOR UPDATE", {"id": entity_id}
            )
            if not entities:
                raise LookupError("Entity not found.")
            if context is not None:
                await agent_runs.validate_evidence(session, context)
            stats = {"claims": 0, "applied": 0, "abstained": 1, "strategy": "abstain"}
            if result.strategy != "abstain":
                stats = await persist_proposals(
                    session,
                    value=value,
                    result=result,
                    step_id=step_id,
                    entity_id=entity_id,
                    artifacts=artifacts,
                    observation_id=observation_id,
                    apply=apply,
                    min_confidence=min_confidence,
                )
            await agent_runs.finish_step(
                session,
                step_id,
                result.model_dump(mode="json"),
                error=result.summary if failed else "",
            )
            return stats
    except Exception as error:
        async with session_scope() as session:
            await agent_runs.finish_step(
                session,
                step_id,
                result.model_dump(mode="json") if result is not None else None,
                error=f"{type(error).__name__}: {error}",
            )
        raise
