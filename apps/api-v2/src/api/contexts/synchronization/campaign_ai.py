"""Bounded, restartable AI phases for durable provider campaigns."""

import json
import os
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index.resolution import cluster_ids
from api.contexts.knowledge import agent_runs, enrichment, normalization
from api.contexts.knowledge.agent_runs import EvidenceContext, WriteGuard
from api.contexts.knowledge.enrichment_models import CompletionInput
from api.contexts.knowledge.normalization import NormalizationInput
from api.contexts.presentation.fragments import fetch
from api.contexts.synchronization import campaigns
from api.contexts.synchronization.discovery_step import positive_int
from api.contexts.synchronization.domain import PROVIDER_NAMESPACES, LeaseLost
from api.worker.session import session_scope


class AIRequiredError(RuntimeError):
    """A required normalization could not produce a model or reviewed-alias result."""


@dataclass(frozen=True, slots=True)
class SourceTarget:
    entity_id: UUID
    observation_id: UUID
    namespace: str
    external_id: str
    normalized: dict[str, Any]
    payload: dict[str, Any]


async def ensure_run(session: AsyncSession, campaign: Any) -> UUID:
    if campaign.agent_run_id is not None:
        return UUID(str(campaign.agent_run_id))
    run_id = await agent_runs.create_run(
        session,
        title=f"{campaign.provider_slug} {campaign.campaign_type}",
        scope=f"sync:{campaign.id}",
        key=str(campaign.id),
        metadata={
            "campaign_id": str(campaign.id),
            "provider": campaign.provider_slug,
            "ai_mode": campaign.ai_mode,
            "scopes": ["knowledge:read"],
        },
    )
    await fetch(
        session,
        "UPDATE sync_campaign SET agent_run_id=:run,updated_at=now() WHERE id=:id RETURNING id",
        {"id": campaign.id, "run": run_id},
    )
    return run_id


async def source_target(session: AsyncSession, campaign: Any, item: Any) -> SourceTarget | None:
    identifier = (item.result or {}).get("entity_id")
    if not identifier:
        return None
    entity_id = UUID(str(identifier))
    members = await cluster_ids(session, entity_id)
    rows = await fetch(
        session,
        """
        SELECT o.id AS observation_id,o.normalized_data,v.payload,ns.slug AS namespace,r.external_id
        FROM provider_record r JOIN provider_namespace ns ON ns.id=r.namespace_id
        JOIN provider p ON p.id=ns.provider_id
        JOIN LATERAL (
          SELECT observation.id,observation.normalized_data,mapping.revision_id
          FROM provider_observation observation
          JOIN provider_current_observation current ON current.observation_id=observation.id
          LEFT JOIN mapping_run mapping ON mapping.id=observation.mapping_run_id
          WHERE observation.provider_record_id=r.id AND current.schema_name='index.work'
          ORDER BY current.updated_at DESC,current.id DESC LIMIT 1
        ) o ON true LEFT JOIN provider_revision v
          ON v.id=COALESCE(o.revision_id,r.latest_revision_id)
        WHERE p.slug=:provider AND ns.slug=:namespace AND r.external_id=:external
          AND EXISTS (SELECT 1 FROM entity_representation e WHERE e.provider_record_id=r.id
                      AND e.entity_id=ANY(:members) AND e.is_active)
        """,
        {
            "provider": campaign.provider_slug,
            "namespace": PROVIDER_NAMESPACES[campaign.provider_slug],
            "external": item.cursor,
            "members": list(members),
        },
    )
    if not rows:
        return None
    row = rows[0]
    return SourceTarget(
        entity_id,
        row.observation_id,
        row.namespace,
        row.external_id,
        row.normalized_data or {},
        row.payload or {},
    )


def taxonomy_values(payload: dict[str, Any]) -> tuple[str, ...]:
    values = []
    for value in payload.get("genres") or []:
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    for item in payload.get("tags") or []:
        value = item.get("name") if isinstance(item, dict) else item
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return tuple(dict.fromkeys(values))


def write_guard(campaign_id: UUID, owner: str, phase: str) -> WriteGuard:
    async def guard(session: AsyncSession) -> None:
        await campaigns.owned(session, campaign_id, owner, phase=phase, allow_paused=True)
        if not await campaigns.heartbeat(session, campaign_id, owner, lease_seconds=1200):
            raise LeaseLost("Campaign lease expired before renewal.")

    return guard


async def completed_normalization(
    session: AsyncSession, target: SourceTarget, run_id: UUID, value: NormalizationInput
) -> normalization.NormalizationResult | None:
    rows = await fetch(
        session,
        """
        SELECT s.output FROM agent_step s JOIN ai_claim c ON c.step_id=s.id
        JOIN claim_evidence e ON e.claim_id=c.id
        WHERE s.run_id=:run AND s.skill_name='field_normalization' AND s.input_hash=:hash
          AND c.target_entity_id=:entity AND e.observation_id=:observation
          AND s.output IS NOT NULL ORDER BY s.sequence DESC LIMIT 1
        """,
        {
            "run": run_id,
            "hash": agent_runs.payload_hash(value.model_dump(mode="json")),
            "entity": target.entity_id,
            "observation": target.observation_id,
        },
    )
    if not rows:
        return None
    return normalization.NormalizationResult.model_validate(rows[0].output)


async def normalize_item(campaign_id: UUID, item: Any, owner: str, deadline: float) -> bool:
    async with session_scope() as session:
        campaign = await campaigns.owned(session, campaign_id, owner, phase="normalizing")
        target = await source_target(session, campaign, item)
        if target is None:
            return True
        values = taxonomy_values(target.payload)
        if not values:
            return True
        run_id = await ensure_run(session, campaign)
    guard = write_guard(campaign_id, owner, "normalizing")
    for text in values:
        async with session_scope() as session:
            current = await campaigns.owned(session, campaign_id, owner, phase="normalizing")
            value = NormalizationInput(
                vocabulary="provider-tag",
                source_text=text,
                provider_namespace=target.namespace,
                context={"provider": campaign.provider_slug},
            )
            previous = await completed_normalization(session, target, run_id, value)
            if not await campaigns.heartbeat(session, campaign_id, owner, lease_seconds=1200):
                raise LeaseLost("Campaign lease expired before renewal.")
        if previous is not None and not (
            current.ai_mode == "required" and previous.source == "raw"
        ):
            continue
        if monotonic() >= deadline:
            return False
        result = await normalization.normalize(
            value,
            evidence=EvidenceContext(
                target.entity_id, run_id, observation_id=target.observation_id
            ),
            before_write=guard,
        )
        if campaign.ai_mode == "required" and result.source == "raw":
            raise AIRequiredError(
                "Required AI normalization did not produce a model or alias result."
            )
    return True


async def enrich_item(campaign_id: UUID, item: Any, owner: str) -> dict[str, Any]:
    async with session_scope() as session:
        campaign = await campaigns.owned(session, campaign_id, owner, phase="enriching")
        target = await source_target(session, campaign, item)
        if target is None:
            return {"claims": 0, "applied": 0, "abstained": 0, "skipped": 1}
        members = await cluster_ids(session, target.entity_id)
        rows = await fetch(
            session,
            "SELECT language,text FROM entity_name WHERE entity_id=ANY(:ids) ORDER BY id",
            {"ids": list(members)},
        )
        names = {row.language: row.text for row in rows if row.language}
        descriptions = await fetch(
            session,
            "SELECT DISTINCT language FROM entity_description WHERE entity_id=ANY(:ids)",
            {"ids": list(members)},
        )
        existing_descriptions = {row.language for row in descriptions}
        params = campaign.parameters or {}
        languages = tuple(
            params.get("enrich_languages")
            or [
                language.strip()
                for language in os.environ.get("AI_ENRICH_LANGUAGES", "zh,ja,en").split(",")
                if language.strip()
            ]
        )
        missing = [f"title:{lang}" for lang in languages if lang not in names]
        missing += [
            f"description:{lang}" for lang in languages if lang not in existing_descriptions
        ]
        if not missing:
            return {"claims": 0, "applied": 0, "abstained": 0, "strategy": "skipped"}
        data = target.normalized
        preferred = str(
            data.get("title_cn") or data.get("name_cn") or next(iter(names.values()), "")
        )
        value = CompletionInput(
            entity_id=str(target.entity_id),
            provider=campaign.provider_slug,
            external_id=target.external_id,
            preferred_name=preferred,
            original_name=str(data.get("title") or data.get("name") or ""),
            source_language="",
            release_date=str(data.get("date") or ""),
            missing_fields=missing,
            existing_names=names,
        )
        run_id = await ensure_run(session, campaign)
        apply = bool(
            params.get(
                "enrich_apply",
                os.environ.get("AI_ENRICH_APPLY", "false").lower() in {"1", "true", "yes", "on"},
            )
        )
        confidence = float(
            params.get("enrich_min_confidence", os.environ.get("AI_ENRICH_MIN_CONFIDENCE", "0.85"))
        )
    return await enrichment.complete(
        value,
        run_id=run_id,
        observation_id=target.observation_id,
        apply=apply,
        min_confidence=confidence,
        before_write=write_guard(campaign_id, owner, "enriching"),
    )


async def run_phase(campaign_id: UUID, owner: str, phase: str, *, deadline: float) -> bool:
    timestamp = {"normalizing": "ai_processed_at", "enriching": "ai_enriched_at"}[phase]
    async with session_scope() as session:
        campaign = await campaigns.owned(session, campaign_id, owner, phase=phase)
        if campaign.ai_mode == "off":
            return True
        params = campaign.parameters or {}
        limit = positive_int(params.get("ai_batch_size"), 50)
        configured = params.get("ai_sample_size")
        if phase == "enriching":
            configured = params.get(
                "enrich_sample_size", os.environ.get("AI_ENRICH_SAMPLE_SIZE", "200")
            )
        sample = int(configured) if configured is not None else 0
        processed = (
            await fetch(
                session,
                f"SELECT count(*) AS n FROM sync_work_item WHERE "
                f"campaign_id=:id AND {timestamp} IS NOT NULL",
                {"id": campaign_id},
            )
        )[0].n
        if sample > 0:
            if processed >= sample:
                return True
            limit = min(limit, sample - processed)
        items = await fetch(
            session,
            f"SELECT * FROM sync_work_item WHERE campaign_id=:id "
            f"AND status='succeeded' AND {timestamp} IS NULL ORDER BY shard,id LIMIT :limit",
            {"id": campaign_id, "limit": limit},
        )
    for item in items:
        if monotonic() >= deadline:
            return False
        result = None
        if phase == "normalizing":
            if not await normalize_item(campaign_id, item, owner, deadline):
                return False
        else:
            result = await enrich_item(campaign_id, item, owner)
        async with session_scope() as session:
            campaign = await campaigns.owned(
                session, campaign_id, owner, phase=phase, allow_paused=True
            )
            await fetch(
                session,
                f"UPDATE sync_work_item SET {timestamp}=now(),updated_at=now() "
                "WHERE id=:id RETURNING id",
                {"id": item.id},
            )
            if result is not None:
                parameters = dict(campaign.parameters or {})
                stats = dict(parameters.get("enrichment") or {})
                for key in ("claims", "applied", "abstained", "skipped"):
                    stats[key] = stats.get(key, 0) + int(result.get(key, 0))
                parameters["enrichment"] = stats
                await fetch(
                    session,
                    "UPDATE sync_campaign SET parameters=CAST(:params AS jsonb),"
                    "updated_at=now() WHERE id=:id RETURNING id",
                    {"id": campaign_id, "params": json.dumps(parameters)},
                )
            if not await campaigns.heartbeat(session, campaign_id, owner, lease_seconds=1200):
                raise LeaseLost("Campaign lease expired before renewal.")
            processed += 1
            if campaign.status == "paused":
                return False
    if sample > 0 and processed >= sample:
        return True
    async with session_scope() as session:
        pending = await fetch(
            session,
            f"SELECT 1 FROM sync_work_item WHERE campaign_id=:id "
            f"AND status='succeeded' AND {timestamp} IS NULL LIMIT 1",
            {"id": campaign_id},
        )
        return not bool(pending)
