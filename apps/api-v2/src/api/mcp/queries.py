"""Async projections shared by the public and internal MCP tools."""

from typing import Any
from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError

from api.contexts.identity import resolution
from api.contexts.knowledge import retrieval
from api.contexts.presentation.fragments import fetch
from api.contexts.presentation.relations import CURRENT_RELATION
from api.contexts.presentation.summary import entity_summary
from api.worker.session import session_scope


async def search_public_entities(
    *, query: str = "", collection: str = "", language: str = "", limit: int = 20
) -> dict[str, Any]:
    value = retrieval.SearchEntitiesInput(
        query=query.strip()[:256],
        collection=collection.strip()[:64],
        language=language[:35],
        limit=max(1, min(limit, 50)),
    )
    return (await retrieval.search_entities(value)).model_dump(mode="json")


async def get_public_entity(*, entity_id: UUID, language: str = "") -> dict[str, Any]:
    try:
        result = await retrieval.get_entity(
            retrieval.GetEntityInput(entity_id=entity_id, language=language[:35])
        )
    except LookupError as error:
        raise ToolError("Public entity not found.") from error
    async with session_scope() as session:
        root = UUID(result.entity["id"])
        cluster = list(await resolution.cluster_ids(session, root))
        memberships = await fetch(
            session,
            "SELECT c.slug AS collection,c.name,m.listing_state,m.inclusion_reason "
            "FROM curated_membership m JOIN curated_collection c ON c.id=m.collection_id "
            "WHERE m.entity_id=ANY(:ids) AND m.listing_state='listed' ORDER BY c.slug,m.entity_id",
            {"ids": cluster},
        )
        redirects = await fetch(
            session,
            "SELECT source_entity_id FROM entity_redirect WHERE target_entity_id=ANY(:ids) "
            "AND is_active ORDER BY source_entity_id",
            {"ids": cluster},
        )
    return {
        **result.entity,
        "memberships": [dict(row._mapping) for row in memberships],
        "merged_from": [{"entity_id": str(row.source_entity_id)} for row in redirects],
        "is_merged": bool(redirects) or len(result.entity["sources"]) > 1,
    }


async def get_public_relations(*, entity_id: UUID, language: str = "") -> dict[str, Any]:
    await get_public_entity(entity_id=entity_id, language=language)
    async with session_scope() as session:
        root = await resolution.resolve(session, entity_id)
        if root is None or not await resolution.is_active(session, root):
            raise ToolError("Public entity not found.")
        members = await resolution.cluster_ids(session, root)
        if not await resolution.is_public(session, members):
            raise ToolError("Public entity not found.")
        rows = await fetch(
            session,
            "SELECT relation.relation_type,relation.to_entity_id FROM entity_relation relation "
            "WHERE relation.from_entity_id=ANY(:ids) AND "
            + CURRENT_RELATION
            + " ORDER BY relation.id LIMIT 100",
            {"ids": list(members)},
        )
        results = []
        seen = set()
        for row in rows:
            target = await resolution.resolve(session, row.to_entity_id)
            if target is None or not await resolution.is_active(session, target):
                continue
            cluster = await resolution.cluster_ids(session, target)
            if not await resolution.is_public(session, cluster):
                continue
            key = (row.relation_type, target)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "relation_type": row.relation_type,
                    "target": await entity_summary(
                        session,
                        root=target,
                        cluster_ids=[str(value) for value in cluster],
                        language=language[:35],
                    ),
                }
            )
    return {"results": results}


async def get_match_candidate(candidate_id: UUID) -> dict[str, Any]:
    async with session_scope() as session:
        rows = await fetch(
            session, "SELECT * FROM match_candidate WHERE id=:id", {"id": candidate_id}
        )
        if not rows:
            raise ToolError("Match candidate not found.")
        candidate = rows[0]
        sides = []
        for entity_id in [candidate.left_entity_id, candidate.right_entity_id]:
            root = await resolution.resolve(session, entity_id)
            if root is None:
                raise ToolError("Match candidate entity not found.")
            cluster = await resolution.cluster_ids(session, root)
            sides.append(
                await entity_summary(
                    session, root=root, cluster_ids=[str(value) for value in cluster], language=""
                )
            )
        evidence = await fetch(
            session,
            "SELECT evidence_type,value,weight FROM match_evidence "
            "WHERE candidate_id=:id ORDER BY id",
            {"id": candidate_id},
        )
        return {
            "id": str(candidate.id),
            "status": candidate.status,
            "score": str(candidate.score),
            "runner_up_margin": str(candidate.runner_up_margin),
            "policy_version": candidate.policy_version,
            "hard_conflicts": candidate.hard_conflicts,
            "left_entity": sides[0],
            "right_entity": sides[1],
            "evidence": [
                {"evidence_type": row.evidence_type, "value": row.value, "weight": str(row.weight)}
                for row in evidence
            ],
        }
