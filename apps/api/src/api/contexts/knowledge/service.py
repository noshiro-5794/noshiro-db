"""Classification and extraction with source permissions and durable inference audit."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.index import resolution
from api.contexts.knowledge.domain import Classification, Extraction
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.fragments import fetch
from api.shared.ai import complete_json
from api.shared.inference import fail_run, optional_number, start_run
from api.worker.session import session_scope

MAX_INPUT_BYTES = 100_000
CLASSIFICATION_PROMPT = (
    "Classify a public knowledge-base work using only the supplied safe "
    "projection. Return a JSON object with work_type, confidence, and a "
    "concise reason. work_type must be anime, galgame, manga, novel, game, "
    "music, other, unclassified, or abstain. Never infer private identities."
)
EXTRACTION_PROMPT = (
    "Extract only explicitly stated facts from the supplied provider "
    "observation. Return a JSON object with a claims array. Each claim must "
    "contain predicate, value, value_type, language, spoiler_level, safety, "
    "json_pointer, and confidence. Use an empty claims array when evidence is "
    "insufficient. Do not infer aliases, private identities, or unstated facts."
)


class InputNotAllowed(ValueError):
    """The requested data cannot be processed by the AI workflow."""


async def target(session: AsyncSession, entity_id: str) -> tuple[Any, set[Any], bool]:
    root = await resolution.resolve(session, UUID(entity_id))
    rows = await fetch(session, "SELECT id, kind FROM entity WHERE id = :id", {"id": root})
    if not rows:
        raise LookupError("Entity not found.")
    cluster = await resolution.cluster_ids(session, root)
    restricted = await fetch(
        session,
        "SELECT 1 FROM entity WHERE id = ANY(:ids) AND visibility <> 'public' LIMIT 1",
        {"ids": list(cluster)},
    )
    return rows[0], cluster, not bool(restricted)


async def persist_proposal(
    session: AsyncSession,
    *,
    run_id: UUID,
    use_case: str,
    entity_id: Any,
    observation_id: Any,
    output: dict[str, Any],
    confidence: Decimal,
    abstained: bool,
    reason: str | None = None,
) -> str:
    policy_reason = reason or (
        "The model abstained; no canonical write was performed."
        if abstained
        else "Shadow proposal only; no canonical write was performed."
    )
    rows = await fetch(
        session,
        """
        INSERT INTO ai_proposal (id, run_id, target_entity_id, source_observation_id,
          proposal_type, payload, confidence, status, policy_reason, created_at, decided_at)
        VALUES (gen_random_uuid(), :run, :entity, :observation, :use_case, CAST(:payload AS jsonb),
          :confidence, :status, :reason, now(), CASE WHEN :abstained THEN now() ELSE NULL END)
        RETURNING id
    """,
        {
            "run": run_id,
            "entity": entity_id,
            "observation": observation_id,
            "use_case": use_case,
            "payload": json.dumps(output),
            "confidence": confidence,
            "status": "abstained" if abstained else "pending",
            "reason": policy_reason,
            "abstained": abstained,
        },
    )
    return str(rows[0].id)


async def abstain(
    session: AsyncSession,
    *,
    use_case: str,
    prompt_version: str,
    metadata: dict[str, Any],
    entity_id: Any,
    output: dict[str, Any],
    observation_id: Any = None,
) -> str:
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    rows = await fetch(
        session,
        """
        INSERT INTO ai_run (id, use_case, provider, model, prompt_version, input_hash,
          input_metadata, output, status, error, created_at, started_at, finished_at)
        VALUES (gen_random_uuid(), :use_case, 'policy_gate', 'none', :prompt, :hash,
          CAST(:metadata AS jsonb), CAST(:output AS jsonb), 'abstained', '', now(), now(), now())
        RETURNING id
    """,
        {
            "use_case": use_case,
            "prompt": prompt_version,
            "hash": digest,
            "metadata": json.dumps(metadata),
            "output": json.dumps(output),
        },
    )
    return await persist_proposal(
        session,
        run_id=rows[0].id,
        use_case=use_case,
        entity_id=entity_id,
        observation_id=observation_id,
        output=output,
        confidence=Decimal(0),
        abstained=True,
        reason=output["reason"],
    )


async def complete(
    *,
    use_case: str,
    prompt_version: str,
    metadata: dict[str, Any],
    system: str,
    payload: dict[str, Any],
    entity_id: Any,
    observation_id: Any = None,
) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
    ).encode()
    if len(encoded) > MAX_INPUT_BYTES:
        raise InputNotAllowed(f"AI input exceeds the {MAX_INPUT_BYTES}-byte safety limit.")
    # Normalize values such as dates before both hashing and transmission.
    payload = json.loads(encoded)
    run_id = await start_run(
        payload=payload, use_case=use_case, prompt_version=prompt_version, metadata=metadata
    )
    started = monotonic()
    try:
        raw, usage = await complete_json(system=system, payload=payload)
        if use_case == "entity_classification":
            classification = Classification.model_validate(raw)
            output = classification.model_dump(mode="json")
            confidence = classification.confidence
            abstained = classification.work_type == "abstain"
        else:
            extraction = Extraction.model_validate(raw)
            output = extraction.model_dump(mode="json")
            confidence = extraction.confidence
            abstained = not extraction.claims
        async with session_scope() as session:
            await fetch(
                session,
                """
                UPDATE ai_run SET status = 'succeeded', output = CAST(:output AS jsonb),
                  input_tokens = :input, output_tokens = :output_tokens, cost = :cost,
                  latency_ms = :latency, finished_at = now() WHERE id = :id RETURNING id
            """,
                {
                    "id": run_id,
                    "output": json.dumps(output),
                    "input": optional_number(
                        usage.get("input_tokens", usage.get("prompt_tokens")), integer=True
                    ),
                    "output_tokens": optional_number(
                        usage.get("output_tokens", usage.get("completion_tokens")), integer=True
                    ),
                    "cost": optional_number(usage.get("cost")),
                    "latency": max(0, int((monotonic() - started) * 1000)),
                },
            )
            return await persist_proposal(
                session,
                run_id=run_id,
                use_case=use_case,
                entity_id=entity_id,
                observation_id=observation_id,
                output=output,
                confidence=confidence,
                abstained=abstained,
            )
    except Exception as error:
        await fail_run(run_id, error)
        raise


async def classify_entity(entity_id: str) -> str:
    use_case = "entity_classification"
    version = "entity-classification-v1"
    async with session_scope() as session:
        entity, cluster, public = await target(session, entity_id)
        if entity.kind != "work":
            raise InputNotAllowed("Only work entities can be classified.")
        metadata = {"entity_id": str(entity.id)}
        reason = None
        if not public:
            reason = "Restricted entities cannot be sent to an AI provider."
        else:
            providers = await fetch(
                session,
                """
                SELECT DISTINCT p.slug FROM entity_representation rep
                JOIN provider_record r ON r.id = rep.provider_record_id
                JOIN provider_namespace ns ON ns.id = r.namespace_id
                JOIN provider p ON p.id = ns.provider_id
                WHERE rep.entity_id = ANY(:ids) AND rep.is_active
                  AND p.ai_usage_policy <> 'allowed' ORDER BY p.slug
            """,
                {"ids": list(cluster)},
            )
            if providers:
                reason = (
                    "Every represented provider must explicitly allow AI processing; "
                    f"blocked by: {', '.join(row.slug for row in providers)}."
                )
        if reason:
            return await abstain(
                session,
                use_case=use_case,
                prompt_version=version,
                metadata=metadata,
                entity_id=entity.id,
                output={"work_type": "abstain", "confidence": "0", "reason": reason},
            )
        payload = await entity_detail(
            session, root=entity.id, cluster_ids=list(cluster), language=""
        )
    return await complete(
        use_case=use_case,
        prompt_version=version,
        metadata=metadata,
        system=CLASSIFICATION_PROMPT,
        payload=payload,
        entity_id=entity.id,
    )


async def extract_evidence(observation_id: str, entity_id: str) -> str:
    use_case = "evidence_extraction"
    version = "evidence-extraction-v1"
    async with session_scope() as session:
        entity, cluster, public = await target(session, entity_id)
        rows = await fetch(
            session,
            """
            SELECT o.*, p.slug AS provider_slug, p.ai_usage_policy FROM provider_observation o
            JOIN provider_record r ON r.id = o.provider_record_id
            JOIN provider_namespace ns ON ns.id = r.namespace_id
            JOIN provider p ON p.id = ns.provider_id WHERE o.id = :id
        """,
            {"id": UUID(observation_id)},
        )
        if not rows:
            raise LookupError("Observation not found.")
        observation = rows[0]
        active = await fetch(
            session,
            """
            SELECT 1 FROM entity_representation WHERE provider_record_id = :record
              AND entity_id = ANY(:ids) AND is_active LIMIT 1
        """,
            {"record": observation.provider_record_id, "ids": list(cluster)},
        )
        if not active:
            raise InputNotAllowed(
                "Observation is not an active representation of the target entity."
            )
        current = await fetch(
            session,
            """
            SELECT 1 FROM provider_current_observation
            WHERE provider_record_id = :record AND observation_id = :observation
        """,
            {"record": observation.provider_record_id, "observation": observation.id},
        )
        if not current:
            raise InputNotAllowed("Only a current observation can be processed.")
        metadata = {
            "entity_id": str(entity.id),
            "observation_id": str(observation.id),
            "provider": observation.provider_slug,
        }
        reason = None
        if observation.ai_usage_policy != "allowed":
            reason = "Provider policy does not explicitly allow AI processing."
        elif not public:
            reason = "Restricted entities cannot be sent to an AI provider."
        if reason:
            return await abstain(
                session,
                use_case=use_case,
                prompt_version=version,
                metadata=metadata,
                entity_id=entity.id,
                observation_id=observation.id,
                output={"claims": [], "reason": reason},
            )
        payload = {
            "entity_id": str(entity.id),
            "provider": observation.provider_slug,
            "schema_name": observation.schema_name,
            "schema_version": observation.schema_version,
            "normalized_data": observation.normalized_data,
        }
    return await complete(
        use_case=use_case,
        prompt_version=version,
        metadata=metadata,
        system=EXTRACTION_PROMPT,
        payload=payload,
        entity_id=entity.id,
        observation_id=observation.id,
    )
