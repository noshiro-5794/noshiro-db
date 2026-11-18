"""Reviewed-alias and model vocabulary normalization with source-backed claims."""

import unicodedata
from time import monotonic
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.knowledge import agent_runs
from api.contexts.knowledge.agent_runs import EvidenceContext, WriteGuard
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization.terms import normalize_key
from api.shared.ai import complete_json
from api.shared.inference import fail_run, finish_run, start_run
from api.worker.session import session_scope

SYSTEM_PROMPT = """You normalize provider vocabulary for a knowledge base.
Use only the supplied raw value and context. Never invent an existing term slug.
Choose preserve_raw or abstain when the value is a title, identifier, or ambiguous.
Return JSON matching the supplied schema with action, confidence, and reason.
"""


class NormalizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vocabulary: str = Field(min_length=1, max_length=64)
    source_text: str = Field(min_length=1, max_length=256)
    provider_namespace: str = Field(default="", max_length=128)
    language: str = Field(default="", max_length=35)
    context: dict[str, Any] = Field(default_factory=dict)


class ProposedLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = Field(min_length=1, max_length=35)
    script: str = Field(default="", max_length=8)
    text: str = Field(min_length=1, max_length=256)
    is_preferred: bool = False


class NormalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["map_existing", "propose_new", "preserve_raw", "abstain"]
    normalized_key: str = Field(default="", max_length=256)
    preferred_term: str = Field(default="", max_length=256)
    language: str = Field(default="", max_length=35)
    script: str = Field(default="", max_length=8)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=2000)
    existing_term_slug: str = Field(default="", max_length=128)
    proposed_labels: list[ProposedLabel] = Field(default_factory=list, max_length=16)
    source: Literal["alias", "model", "raw", "abstain"]


def detect_language(value: str) -> str:
    for char in value:
        name = unicodedata.name(char, "")
        if "HIRAGANA" in name or "KATAKANA" in name:
            return "ja"
        if "HANGUL" in name:
            return "ko"
        if "CJK" in name:
            return "zh"
    return "en"


async def reviewed_alias(
    session: AsyncSession, value: NormalizationInput, key: str, language: str
) -> NormalizationResult | None:
    rows = await fetch(
        session,
        """
        SELECT a.*,t.slug AS term_slug FROM index_term_alias a
        JOIN taxonomy_term t ON t.id=a.term_id
        LEFT JOIN provider_namespace ns ON ns.id=a.provider_namespace_id
        WHERE a.vocabulary=:vocabulary AND a.normalized_key=:key AND a.is_reviewed
          AND a.language=ANY(:languages)
          AND ((:namespace='' AND a.provider_namespace_id IS NULL) OR ns.slug=:namespace)
        ORDER BY a.confidence DESC,a.id LIMIT 1
        """,
        {
            "vocabulary": value.vocabulary,
            "key": key,
            "languages": [language, ""],
            "namespace": value.provider_namespace,
        },
    )
    if not rows:
        return None
    alias = rows[0]
    return NormalizationResult(
        action="map_existing",
        normalized_key=alias.normalized_key,
        preferred_term=alias.preferred_term,
        language=alias.language or language,
        script=alias.script,
        confidence=float(alias.confidence),
        reason="Matched a reviewed provider vocabulary alias.",
        existing_term_slug=alias.term_slug,
        source="alias",
    )


async def model_result(
    value: NormalizationInput, key: str, language: str, step_id: UUID | None
) -> NormalizationResult:
    payload = {
        "vocabulary": value.vocabulary,
        "source_text": value.source_text,
        "normalized_key": key,
        "provider_namespace": value.provider_namespace,
        "language": language,
        "context": value.context,
    }
    run_id = None
    if step_id is not None:
        run_id = await start_run(
            payload=payload,
            use_case="field_normalization",
            prompt_version="field-normalization-v1",
            metadata={"skill": "field_normalization"},
            agent_step_id=step_id,
        )
    started = monotonic()
    try:
        raw, usage = await complete_json(system=SYSTEM_PROMPT, payload=payload)
        result = NormalizationResult.model_validate({**raw, "source": "model"})
    except Exception as error:
        if run_id is not None:
            await fail_run(run_id, error)
        return NormalizationResult(
            action="preserve_raw",
            normalized_key=key,
            preferred_term=value.source_text.strip(),
            language=language,
            confidence=0,
            reason="Model unavailable or returned an invalid contract.",
            source="raw",
        )
    if result.action == "map_existing" and not result.existing_term_slug:
        result = result.model_copy(
            update={
                "action": "propose_new",
                "reason": "Model selected map_existing without a stable term slug.",
            }
        )
    if run_id is not None:
        await finish_run(
            run_id,
            result.model_dump(mode="json"),
            usage,
            latency_ms=max(0, int((monotonic() - started) * 1000)),
        )
    return result


async def normalize(
    value: NormalizationInput,
    *,
    evidence: EvidenceContext | None = None,
    before_write: WriteGuard | None = None,
) -> NormalizationResult:
    key = normalize_key(value.source_text)
    language = value.language or detect_language(value.source_text)
    step_id = None
    async with session_scope() as session:
        if evidence is not None:
            await agent_runs.validate_evidence(session, evidence)
            step_id = await agent_runs.create_step(
                session,
                run_id=evidence.run_id,
                skill="field_normalization",
                payload=value.model_dump(mode="json"),
            )
        result = await reviewed_alias(session, value, key, language)
    if result is None:
        result = await model_result(value, key, language, step_id)
    if evidence is not None and step_id is not None:
        failure = None
        async with session_scope() as session:
            try:
                if before_write is not None:
                    await before_write(session)
                await agent_runs.record_claim(
                    session,
                    context=evidence,
                    step_id=step_id,
                    claim_type="field_normalization",
                    predicate=f"taxonomy:{value.vocabulary}",
                    value=result.model_dump(mode="json"),
                    confidence=result.confidence,
                    evidence_strength=1 if result.source == "alias" else 0,
                    locator="/source_text",
                    excerpt=value.source_text,
                    excerpt_hash=agent_runs.payload_hash({"source_text": value.source_text}),
                )
            except Exception as error:
                failure = error
            reason = result.reason if result.source == "raw" else ""
            if failure is not None:
                reason = f"{type(failure).__name__}: {failure}"
            await agent_runs.finish_step(
                session, step_id, result.model_dump(mode="json"), error=reason
            )
        if failure is not None:
            raise failure
    return result
