"""A sync campaign with the throughput it is currently achieving."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch, isoformat

QUERY = """
    SELECT campaign.id, campaign.provider_slug, campaign.campaign_type,
           campaign.status, campaign.ai_mode, campaign.parameters,
           campaign.total_items, campaign.processed_items, campaign.synced_items,
           campaign.skipped_items, campaign.failed_items,
           campaign.quality_report, campaign.cost, campaign.error,
           campaign.heartbeat_at, campaign.next_run_at, campaign.created_at,
           campaign.started_at, campaign.finished_at, campaign.updated_at,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'queued')
             AS queued,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'running')
             AS running,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'succeeded')
             AS succeeded,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.status = 'failed')
             AS failed,
           (SELECT count(*) FROM sync_work_item AS item
             WHERE item.campaign_id = campaign.id AND item.next_retry_at IS NOT NULL)
             AS retry_waiting,
           EXTRACT(EPOCH FROM (now() - campaign.started_at)) AS elapsed_seconds
    FROM sync_campaign AS campaign WHERE campaign.id = CAST(:id AS uuid)
"""


def _payload(row: Any) -> dict[str, Any]:
    elapsed = float(row.elapsed_seconds or 0)
    throughput = row.processed_items / elapsed if elapsed > 0 else None
    remaining = max(0, row.total_items - row.processed_items)
    percent = round(row.processed_items / row.total_items * 100, 2) if row.total_items else None
    return {
        "id": str(row.id),
        "provider_slug": row.provider_slug,
        "campaign_type": row.campaign_type,
        "status": row.status,
        "ai_mode": row.ai_mode,
        "parameters": row.parameters if isinstance(row.parameters, dict) else {},
        "total_items": row.total_items,
        "processed_items": row.processed_items,
        "synced_items": row.synced_items,
        "skipped_items": row.skipped_items,
        "failed_items": row.failed_items,
        "quality_report": row.quality_report,
        "cost": float(row.cost) if row.cost is not None else None,
        "error": row.error,
        "heartbeat_at": isoformat(row.heartbeat_at),
        "next_run_at": isoformat(row.next_run_at),
        "created_at": isoformat(row.created_at),
        "started_at": isoformat(row.started_at),
        "finished_at": isoformat(row.finished_at),
        "updated_at": isoformat(row.updated_at),
        "progress": {
            "percent": percent,
            "queued": int(row.queued),
            "running": int(row.running),
            "succeeded": int(row.succeeded),
            "failed": int(row.failed),
            "retry_waiting": int(row.retry_waiting),
            "throughput_items_per_second": round(throughput, 4) if throughput is not None else None,
            "eta_seconds": round(remaining / throughput)
            if throughput is not None and throughput > 0
            else None,
        },
    }


async def campaign(session: AsyncSession, *, campaign_id: str) -> dict[str, Any]:
    rows = await fetch(session, QUERY, {"id": campaign_id})
    if not rows:
        raise LookupError(campaign_id)
    return _payload(rows[0])


async def list_campaigns(
    session: AsyncSession, *, provider: str, status: str
) -> list[dict[str, Any]]:
    clauses = ["TRUE"]
    params: dict[str, Any] = {}
    if provider:
        clauses.append("campaign.provider_slug = :provider")
        params["provider"] = provider
    if status:
        clauses.append("campaign.status = :status")
        params["status"] = status
    base = QUERY.split("WHERE")[0]
    rows = await fetch(
        session,
        base + " WHERE " + " AND ".join(clauses) + " ORDER BY campaign.id LIMIT 100",
        params,
    )
    return [_payload(row) for row in rows]


async def campaign_items(
    session: AsyncSession,
    *,
    campaign_id: str,
    status: str,
    page: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    await campaign(session, campaign_id=campaign_id)
    where = "item.campaign_id = CAST(:campaign AS uuid)"
    params: dict[str, Any] = {"campaign": campaign_id}
    if status:
        where += " AND item.status = :status"
        params["status"] = status
    total = await fetch(
        session,
        f"SELECT count(*) AS total FROM sync_work_item AS item WHERE {where}",
        params,
    )
    rows = await fetch(
        session,
        "SELECT item.id, item.shard, item.cursor, item.status,"
        " item.provider_record_id AS provider_record,"
        " item.result, item.error, item.attempt, item.next_retry_at,"
        " item.last_error_code, item.ai_processed_at, item.ai_enriched_at,"
        " item.started_at, item.finished_at, item.updated_at"
        f" FROM sync_work_item AS item WHERE {where}"
        " ORDER BY item.shard, item.id LIMIT :limit OFFSET :offset",
        {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    )
    return int(total[0].total), [
        {
            "id": row.id,
            "shard": row.shard,
            "cursor": row.cursor,
            "status": row.status,
            "provider_record": row.provider_record,
            "result": row.result,
            "error": row.error,
            "attempt": row.attempt,
            "next_retry_at": isoformat(row.next_retry_at),
            "last_error_code": row.last_error_code,
            "ai_processed_at": isoformat(row.ai_processed_at),
            "ai_enriched_at": isoformat(row.ai_enriched_at),
            "started_at": isoformat(row.started_at),
            "finished_at": isoformat(row.finished_at),
            "updated_at": isoformat(row.updated_at),
        }
        for row in rows
    ]


ACTIVE_STATUSES = (
    "queued",
    "discovering",
    "fetching",
    "mapping",
    "normalizing",
    "reconciling",
    "enriching",
    "reviewing",
)


async def summary(session: AsyncSession) -> dict[str, Any]:
    by_status = await fetch(
        session,
        "SELECT status, count(*) AS count FROM sync_campaign GROUP BY status",
        {},
    )
    by_provider = await fetch(
        session,
        "SELECT provider_slug, count(*) AS count FROM sync_campaign GROUP BY provider_slug",
        {},
    )
    stale = await fetch(
        session,
        "SELECT count(*) AS count FROM sync_campaign"
        " WHERE status = ANY(:statuses) AND lease_expires_at < now()",
        {"statuses": list(ACTIVE_STATUSES)},
    )
    items = await fetch(
        session,
        "SELECT count(*) FILTER (WHERE status = 'queued') AS queued,"
        " count(*) FILTER (WHERE status = 'failed') AS failed"
        " FROM sync_work_item",
        {},
    )
    claims = await fetch(
        session,
        "SELECT count(*) AS count FROM ai_claim AS claim"
        " JOIN agent_step AS step ON step.id = claim.step_id"
        " JOIN sync_campaign AS campaign ON campaign.agent_run_id = step.run_id"
        " WHERE claim.status = 'proposed'",
        {},
    )
    return {
        "campaigns_by_status": {row.status: int(row.count) for row in by_status},
        "campaigns_by_provider": {row.provider_slug: int(row.count) for row in by_provider},
        "stale_leases": int(stale[0].count),
        "queued_items": int(items[0].queued),
        "failed_items": int(items[0].failed),
        "pending_ai_claims": int(claims[0].count),
    }


async def campaign_claims(
    session: AsyncSession,
    *,
    campaign_id: str,
    status: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    rows = await fetch(
        session,
        "SELECT agent_run_id FROM sync_campaign WHERE id = CAST(:id AS uuid)",
        {"id": campaign_id},
    )
    if not rows:
        raise LookupError(campaign_id)
    run_id = rows[0].agent_run_id
    if run_id is None:
        return {"count": 0, "results": []}
    where = "step.run_id = :run"
    params: dict[str, Any] = {"run": run_id}
    if status:
        where += " AND claim.status = :status"
        params["status"] = status
    total = await fetch(
        session,
        "SELECT count(*) AS total FROM ai_claim AS claim"
        f" JOIN agent_step AS step ON step.id = claim.step_id WHERE {where}",
        params,
    )
    claims = await fetch(
        session,
        "SELECT claim.id, claim.claim_type, claim.predicate_slug, claim.proposed_value,"
        " claim.model_confidence, claim.evidence_strength, claim.calibrated_confidence,"
        " claim.status, claim.policy_decision, claim.policy_reason, claim.created_at,"
        " claim.decided_at FROM ai_claim AS claim"
        f" JOIN agent_step AS step ON step.id = claim.step_id WHERE {where}"
        " ORDER BY claim.created_at DESC LIMIT :limit OFFSET :offset",
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    ids = [row.id for row in claims]
    evidence: dict[Any, list[dict[str, Any]]] = {claim_id: [] for claim_id in ids}
    if ids:
        links = await fetch(
            session,
            "SELECT link.claim_id, link.locator, link.excerpt, link.excerpt_hash,"
            " link.relevance, link.observation_id, artifact.source_url"
            " FROM claim_evidence AS link"
            " LEFT JOIN source_artifact AS artifact ON artifact.id = link.artifact_id"
            " WHERE link.claim_id = ANY(:ids) ORDER BY link.id",
            {"ids": ids},
        )
        for link in links:
            evidence[link.claim_id].append(
                {
                    "locator": link.locator,
                    "excerpt": link.excerpt,
                    "excerpt_hash": link.excerpt_hash,
                    "relevance": link.relevance,
                    "source_url": link.source_url,
                    "observation": str(link.observation_id)
                    if link.observation_id is not None
                    else None,
                }
            )
    return {
        "count": int(total[0].total),
        "results": [
            {
                "id": claim.id,
                "claim_type": claim.claim_type,
                "predicate_slug": claim.predicate_slug,
                "proposed_value": claim.proposed_value,
                "model_confidence": claim.model_confidence,
                "evidence_strength": claim.evidence_strength,
                "calibrated_confidence": claim.calibrated_confidence,
                "status": claim.status,
                "policy_decision": claim.policy_decision,
                "policy_reason": claim.policy_reason,
                "created_at": isoformat(claim.created_at),
                "decided_at": isoformat(claim.decided_at),
                "evidence": evidence.get(claim.id, []),
            }
            for claim in claims
        ],
    }
