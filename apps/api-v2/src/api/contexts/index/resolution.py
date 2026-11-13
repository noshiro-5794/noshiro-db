"""The resolution engine behind the candidate decision.

A `bind` is not a status update: it follows redirects, picks the canonical side,
records a merge event and a redirect, marks the source merged, and then rebuilds every
fact in the new cluster. The rebuild is why this file exists at all — without it a merge
leaves the fact layer pointing at a cluster that no longer answers.

Ported from `apps/index/services/resolution.py` and `fact_resolution.py`; the SQL is
written by hand for the same reason the rest of this service is.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

MAX_REDIRECT_DEPTH = 32
MAX_CLUSTER_DEPTH = 32
POLICY_VERSION = "fact-resolution-v1"
RULE_METHOD = "rule"

BINDABLE = {
    "anime": {"anime"},
    "galgame": {"galgame", "game"},
    "game": {"galgame", "game"},
}
RESOLVED_STATUS = {
    "bind": "accepted",
    "group": "grouped",
    "reject": "rejected",
    "abstain": "abstained",
}
VISIBILITY_RANK = {"public": 0, "authenticated": 1, "restricted": 2}


class ResolutionError(RuntimeError):
    """A decision the engine refuses to make; the API answers 409."""


class CandidateNotFound(LookupError):
    """No such candidate; the API answers 404."""


async def resolve(session: AsyncSession, entity_id: Any) -> Any:
    """Follow active redirects to the canonical entity."""
    current = entity_id
    seen: set[Any] = set()
    for _ in range(MAX_REDIRECT_DEPTH):
        if current in seen:
            raise ResolutionError("Entity redirect cycle detected.")
        seen.add(current)
        rows = await fetch(
            session,
            "SELECT target_entity_id FROM entity_redirect"
            " WHERE source_entity_id = :id AND is_active ORDER BY created_at LIMIT 1",
            {"id": current},
        )
        if not rows:
            return current
        current = rows[0].target_entity_id
    raise ResolutionError("Entity redirect depth exceeded.")


async def cluster_ids(session: AsyncSession, entity_id: Any) -> set[Any]:
    """The canonical entity and everything redirected into it, transitively."""
    root = await resolve(session, entity_id)
    members = {root}
    frontier = {root}
    for _ in range(MAX_CLUSTER_DEPTH):
        rows = await fetch(
            session,
            "SELECT DISTINCT source_entity_id FROM entity_redirect"
            " WHERE target_entity_id = ANY(:frontier) AND is_active",
            {"frontier": list(frontier)},
        )
        sources = {row.source_entity_id for row in rows} - members
        if not sources:
            return members
        members |= sources
        frontier = sources
    raise ResolutionError("Entity redirect cluster depth exceeded.")


async def _entity(session: AsyncSession, entity_id: Any) -> Any:
    rows = await fetch(
        session,
        "SELECT id, kind, visibility, audience, spoiler_level, created_at"
        " FROM entity WHERE id = :id",
        {"id": entity_id},
    )
    if not rows:
        raise ResolutionError("Entity not found.")
    return rows[0]


def safety_rank(row: Any) -> tuple[int, bool, int]:
    return (
        VISIBILITY_RANK.get(row.visibility, 9),
        row.audience == "adult",
        row.spoiler_level or 0,
    )


async def _library_entries(session: AsyncSession, ids: set[Any]) -> list[Any]:
    return await fetch(
        session,
        "SELECT id, user_id, entity_id FROM user_library_entry"
        " WHERE entity_id = ANY(:ids) ORDER BY id",
        {"ids": list(ids)},
    )


async def _work_types(session: AsyncSession, ids: set[Any]) -> set[str]:
    rows = await fetch(
        session,
        "SELECT DISTINCT work_type FROM work WHERE entity_id = ANY(:ids)",
        {"ids": list(ids)},
    )
    return {row.work_type for row in rows if row.work_type}


def _bindable(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return True
    return any(other in BINDABLE.get(kind, set()) for kind in left for other in right)


async def _canonical_pair(session: AsyncSession, left_id: Any, right_id: Any) -> tuple[Any, Any]:
    left = await _entity(session, await resolve(session, left_id))
    right = await _entity(session, await resolve(session, right_id))
    if left.id == right.id:
        raise ResolutionError("Candidate entities already resolve together.")
    if left.kind != right.kind:
        raise ResolutionError("Cannot bind entities of different kinds.")
    left_ids = await cluster_ids(session, left.id)
    right_ids = await cluster_ids(session, right.id)
    left_types = await _work_types(session, left_ids)
    right_types = await _work_types(session, right_ids)
    if not _bindable(left_types, right_types):
        raise ResolutionError(
            "Cannot bind works from different families: "
            f"{sorted(left_types)} and {sorted(right_types)}."
        )
    counts = {left.id: 0, right.id: 0}
    for row in await _library_entries(session, left_ids | right_ids):
        counts[left.id if row.entity_id in left_ids else right.id] += 1
    left_rank = safety_rank(left)
    right_rank = safety_rank(right)
    if left_rank != right_rank:
        target = left if left_rank > right_rank else right
    elif bool(counts[left.id]) != bool(counts[right.id]):
        target = left if counts[left.id] else right
    else:
        target = min((left, right), key=lambda item: (item.created_at, str(item.id)))
    source = right if target.id == left.id else left
    return source, target


async def _merge_snapshot(session: AsyncSession, source: Any, target: Any) -> dict[str, Any]:
    source_ids = await cluster_ids(session, source.id)
    target_ids = await cluster_ids(session, target.id)
    entries = await _library_entries(session, source_ids | target_ids)
    return {
        "version": 1,
        "source_cluster_ids": sorted(str(value) for value in source_ids),
        "target_cluster_ids": sorted(str(value) for value in target_ids),
        "user_library_entries": [
            {"id": row.id, "user_id": row.user_id, "entity_id": str(row.entity_id)}
            for row in entries
        ],
    }


async def merge(
    session: AsyncSession, *, source_id: Any, target_id: Any, method: str, reason: str
) -> Any:
    source = await _entity(session, await resolve(session, source_id))
    target = await _entity(session, await resolve(session, target_id))
    if source.id == target.id:
        raise ResolutionError("Cannot merge an entity into itself.")
    if source.kind != target.kind:
        raise ResolutionError("Cannot merge entities of different kinds.")
    if safety_rank(source) > safety_rank(target):
        raise ResolutionError("Canonical entity must preserve the strictest safety classification.")
    source_users = {
        row.user_id
        for row in await _library_entries(session, await cluster_ids(session, source.id))
    }
    target_users = {
        row.user_id
        for row in await _library_entries(session, await cluster_ids(session, target.id))
    }
    if source_users & target_users:
        raise ResolutionError("The same user holds library entries on both entities.")
    snapshot = await _merge_snapshot(session, source, target)
    rows = await fetch(
        session,
        "INSERT INTO entity_merge_event (id, source_entity_id, target_entity_id, method, reason,"
        " snapshot, created_at, updated_at)"
        " VALUES (gen_random_uuid(), :source, :target, :method, :reason,"
        " CAST(:snapshot AS jsonb), now(), now()) RETURNING id",
        {
            "source": source.id,
            "target": target.id,
            "method": method,
            "reason": reason,
            "snapshot": json.dumps(snapshot),
        },
    )
    event_id = rows[0].id
    await fetch(
        session,
        "INSERT INTO entity_redirect (source_entity_id, target_entity_id, merge_event_id,"
        " is_active, created_at, updated_at)"
        " VALUES (:source, :target, :event, true, now(), now()) RETURNING id",
        {"source": source.id, "target": target.id, "event": event_id},
    )
    await fetch(
        session,
        "UPDATE entity SET lifecycle = 'merged', updated_at = now() WHERE id = :id RETURNING id",
        {"id": source.id},
    )
    await rebuild_entity(session, target.id)
    return event_id


async def current_facts(session: AsyncSession, ids: set[Any]) -> list[Any]:
    """Facts whose evidence still reflects the current provider mapping."""
    return await fetch(
        session,
        """
        SELECT fact.id, fact.entity_id, fact.predicate_id, fact.language,
               fact.confidence, fact.value_hash,
               (SELECT count(*) FROM fact_evidence AS e WHERE e.fact_id = fact.id)
                 AS evidence_count
        FROM fact
        WHERE fact.entity_id = ANY(:ids) AND fact.status <> 'rejected'
          AND (
            NOT EXISTS (SELECT 1 FROM fact_evidence AS e WHERE e.fact_id = fact.id)
            OR EXISTS (
              SELECT 1 FROM fact_evidence AS e
              JOIN provider_observation AS o ON o.id = e.observation_id
              JOIN provider_record AS r ON r.id = o.provider_record_id
              JOIN provider_namespace AS ns ON ns.id = r.namespace_id
              JOIN provider AS p ON p.id = ns.provider_id
              WHERE e.fact_id = fact.id
                AND p.redistribution_policy <> 'forbidden'
                AND r.status = 'active'
                AND EXISTS (
                  SELECT 1 FROM provider_current_observation AS c
                  WHERE c.observation_id = o.id
                    AND c.provider_record_id = o.provider_record_id
                )
            )
          )
        """,
        {"ids": list(ids)},
    )


def _select(facts: list[Any]) -> tuple[Any, str]:
    if not facts:
        return None, "No current supported fact is available."
    groups: dict[tuple[Any, str], list[Any]] = {}
    for fact in facts:
        groups.setdefault((fact.value_hash, fact.language), []).append(fact)
    ranked = sorted(
        groups.values(),
        key=lambda group: (
            -max(item.confidence for item in group),
            -sum(item.evidence_count for item in group),
            str(min(item.id for item in group)),
        ),
    )
    if len(ranked) > 1:
        first = max(item.confidence for item in ranked[0])
        second = max(item.confidence for item in ranked[1])
        if first == second:
            return None, "Conflicting current facts have equal confidence; abstained."
    selected = sorted(
        ranked[0],
        key=lambda item: (-item.confidence, -item.evidence_count, str(item.id)),
    )[0]
    return selected, "Selected by confidence and independent evidence count."


async def _rebuild(session: AsyncSession, *, root: Any, predicate_id: Any, language: str) -> None:
    ids = await cluster_ids(session, root)
    facts = [
        fact
        for fact in await current_facts(session, ids)
        if fact.predicate_id == predicate_id and fact.language == language
    ]
    facts.sort(key=lambda item: (-item.confidence, item.id))
    selected, reason = _select(facts)
    await fetch(
        session,
        "UPDATE resolution_decision SET is_active = false, updated_at = now()"
        " WHERE entity_id = :root AND predicate_id = :predicate AND language = :language"
        " AND is_active RETURNING id",
        {"root": root, "predicate": predicate_id, "language": language},
    )
    await fetch(
        session,
        "INSERT INTO resolution_decision (entity_id, predicate_id, language,"
        " selected_fact_id, policy_version, reason, is_active, created_at, updated_at)"
        " VALUES (:root, :predicate, :language, :selected, :policy, :reason, true,"
        " now(), now()) RETURNING id",
        {
            "root": root,
            "predicate": predicate_id,
            "language": language,
            "selected": selected.id if selected is not None else None,
            "policy": POLICY_VERSION,
            "reason": reason,
        },
    )
    await fetch(
        session,
        "UPDATE fact SET status = 'candidate', updated_at = now()"
        " WHERE entity_id = ANY(:ids) AND predicate_id = :predicate"
        " AND language = :language AND status <> 'rejected' RETURNING id",
        {"ids": list(ids), "predicate": predicate_id, "language": language},
    )
    if selected is not None:
        await fetch(
            session,
            "UPDATE fact SET status = 'selected', updated_at = now() WHERE id = :id RETURNING id",
            {"id": selected.id},
        )


async def rebuild_fact(
    session: AsyncSession, *, entity_id: Any, predicate_id: Any, language: str
) -> None:
    root = await resolve(session, entity_id)
    await _rebuild(session, root=root, predicate_id=predicate_id, language=language)


async def rebuild_entity(session: AsyncSession, entity_id: Any) -> int:
    root = await resolve(session, entity_id)
    ids = await cluster_ids(session, root)
    fields = {(fact.predicate_id, fact.language) for fact in await current_facts(session, ids)}
    for predicate_id, language in sorted(fields, key=lambda item: (str(item[0]), item[1])):
        await _rebuild(session, root=root, predicate_id=predicate_id, language=language)
    return len(fields)


async def decide(
    session: AsyncSession,
    *,
    candidate_id: Any,
    outcome: str,
    reason: str,
    decided_by: str = "admin_review",
) -> None:
    """Record the decision and, for a bind, do the merge it claims to make."""
    rows = await fetch(
        session,
        "SELECT id, status, left_entity_id, right_entity_id, policy_version"
        " FROM match_candidate WHERE id = :id FOR UPDATE",
        {"id": candidate_id},
    )
    if not rows:
        raise CandidateNotFound(candidate_id)
    candidate = rows[0]
    if candidate.status != "pending":
        raise ResolutionError("Match candidate has already been decided.")
    inserted = await fetch(
        session,
        "INSERT INTO candidate_decision (candidate_id, outcome, decided_by,"
        " policy_version, reason, decision_data, created_at, updated_at)"
        " VALUES (:candidate, :outcome, :by, :policy, :reason, '{}'::jsonb, now(), now())"
        " RETURNING id",
        {
            "candidate": candidate.id,
            "outcome": outcome,
            "by": decided_by,
            "policy": candidate.policy_version,
            "reason": reason,
        },
    )
    decision_id = inserted[0].id
    await fetch(
        session,
        "UPDATE match_candidate SET status = :status, updated_at = now()"
        " WHERE id = :id RETURNING id",
        {"status": RESOLVED_STATUS[outcome], "id": candidate.id},
    )
    if outcome == "bind":
        source, target = await _canonical_pair(
            session, candidate.left_entity_id, candidate.right_entity_id
        )
        event_id = await merge(
            session,
            source_id=source.id,
            target_id=target.id,
            method=RULE_METHOD,
            reason=reason,
        )
        data = json.dumps(
            {
                "merge_event_id": str(event_id),
                "source_entity_id": str(source.id),
                "canonical_entity_id": str(target.id),
            }
        )
    elif outcome == "group":
        data = json.dumps({"grouped_entities": True, "merged": False})
    else:
        return
    await fetch(
        session,
        "UPDATE candidate_decision SET decision_data = CAST(:data AS jsonb),"
        " updated_at = now() WHERE id = :id RETURNING id",
        {"data": data, "id": decision_id},
    )


GROUP_PREFIX = "season-group-"


async def _original_name(session: AsyncSession, entity_id: Any) -> str | None:
    rows = await fetch(
        session,
        "SELECT text FROM entity_name WHERE entity_id = :id AND kind = 'original'"
        " ORDER BY id LIMIT 1",
        {"id": entity_id},
    )
    return rows[0].text if rows else None


async def ensure_pair_group(
    session: AsyncSession, *, left_id: Any, right_id: Any, reason: str
) -> None:
    """Create or reuse the collection that lists two granularity entries together."""
    originals = [
        text
        for text in (
            await _original_name(session, left_id),
            await _original_name(session, right_id),
        )
        if text
    ]
    key = "|".join(sorted(originals)).lower().strip()
    digest = hashlib.sha1(key.encode()).hexdigest()[:12]
    slug = f"{GROUP_PREFIX}{digest}"
    name = f"同季分组 {originals[0][:100]}" if originals else "同季分组"
    rows = await fetch(
        session,
        "SELECT id FROM curated_collection WHERE slug = :slug",
        {"slug": slug},
    )
    if rows:
        collection_id = rows[0].id
    else:
        created = await fetch(
            session,
            "INSERT INTO curated_collection (slug, name, is_enabled, created_at,"
            " updated_at) VALUES (:slug, :name, true, now(), now()) RETURNING id",
            {"slug": slug, "name": name},
        )
        collection_id = created[0].id
    for entity_id in (left_id, right_id):
        exists = await fetch(
            session,
            "SELECT 1 FROM curated_membership WHERE collection_id = :collection"
            " AND entity_id = :entity",
            {"collection": collection_id, "entity": entity_id},
        )
        if exists:
            continue
        await fetch(
            session,
            "INSERT INTO curated_membership (listing_state, inclusion_reason,"
            " collection_id, entity_id, created_at, updated_at)"
            " VALUES ('listed', :reason, :collection, :entity, now(), now())"
            " RETURNING id",
            {"reason": reason, "collection": collection_id, "entity": entity_id},
        )


async def settle_proposal(
    session: AsyncSession, *, candidate_id: Any, accepted: bool, reason: str, grouped: bool
) -> None:
    """The latest proposal for the candidate follows the decision, if still pending."""
    rows = await fetch(
        session,
        "SELECT id, status FROM ai_proposal WHERE match_candidate_id = :candidate"
        " ORDER BY created_at DESC LIMIT 1",
        {"candidate": candidate_id},
    )
    if not rows or rows[0].status != "pending":
        return
    note = f"{reason or 'Admin review'}" + (" (grouped without merge)" if grouped else "")
    await fetch(
        session,
        "UPDATE ai_proposal SET status = :status, policy_reason = :note,"
        " decided_at = now(), updated_at = now() WHERE id = :id RETURNING id",
        {
            "status": "accepted" if accepted else "rejected",
            "note": note,
            "id": rows[0].id,
        },
    )


async def candidate_entities(session: AsyncSession, candidate_id: Any) -> Any:
    rows = await fetch(
        session,
        "SELECT left_entity_id, right_entity_id FROM match_candidate WHERE id = :id",
        {"id": candidate_id},
    )
    if not rows:
        raise CandidateNotFound(candidate_id)
    return rows[0]
