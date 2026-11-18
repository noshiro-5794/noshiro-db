"""Which MAL records have an official AniList twin, and can be bound.

The reconciliation has two halves. This module implements the **discovery** half only:
walk the active MAL representations in id order, resolve them through the redirect graph,
and look up the AniList entity that carries the matching ``anilist-id-mal`` fact. It writes
nothing, so it can be compared against the Django service on a live database.

The binding half (candidates, decisions, merges) is deliberately absent until the
discovery half matches, because a mismatch there would silently merge the wrong pairs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch

ANILIST_ID_MAL_PREDICATE = "anilist-id-mal"
MAL_PROVIDER = "mal"
MAL_NAMESPACE = "anime"


@dataclass
class Discovery:
    mal_entities: int = 0
    examined: int = 0
    anilist_matches: int = 0
    skipped_redirected: int = 0
    pairs: list[tuple[Any, Any, int]] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "mal_entities": self.mal_entities,
            "examined": self.examined,
            "anilist_matches": self.anilist_matches,
            "skipped_redirected": self.skipped_redirected,
        }


async def redirect_map(session: AsyncSession) -> dict[Any, Any]:
    rows = await fetch(
        session,
        "SELECT source_entity_id, target_entity_id FROM entity_redirect WHERE is_active",
        {},
    )
    return {row.source_entity_id: row.target_entity_id for row in rows}


def resolve_with(redirects: dict[Any, Any], entity_id: Any) -> Any:
    """Follow a redirect chain to its root, tolerating a cycle."""
    current = entity_id
    seen: set[Any] = set()
    for _ in range(32):
        if current in seen:
            return entity_id
        seen.add(current)
        target = redirects.get(current)
        if target is None:
            return current
        current = target
    return entity_id


async def mal_representations(session: AsyncSession) -> list[Any]:
    """Active MAL representations, in the same id order the Django service walks."""
    return await fetch(
        session,
        """
        SELECT r.entity_id AS entity_id, pr.external_id AS external_id
        FROM entity_representation AS r
        JOIN provider_record AS pr ON pr.id = r.provider_record_id
        JOIN provider_namespace AS ns ON ns.id = pr.namespace_id
        JOIN provider AS p ON p.id = ns.provider_id
        JOIN entity AS e ON e.id = r.entity_id
        WHERE r.is_active AND p.slug = :provider AND ns.slug = :namespace
          AND pr.status = 'active' AND e.lifecycle = 'active'
        ORDER BY pr.external_id
        """,
        {"provider": MAL_PROVIDER, "namespace": MAL_NAMESPACE},
    )


async def anilist_entities_for_mal_id(session: AsyncSession, mal_id: int) -> list[Any]:
    """Active AniList work entities that claim this official MAL id."""
    return await fetch(
        session,
        """
        SELECT DISTINCT e.id AS id
        FROM fact AS f
        JOIN predicate AS p ON p.id = f.predicate_id
        JOIN entity AS e ON e.id = f.entity_id
        WHERE p.slug = :predicate AND f.value = CAST(:mal AS jsonb)
          AND e.kind = 'work' AND e.lifecycle = 'active'
        ORDER BY e.id
        """,
        {"predicate": ANILIST_ID_MAL_PREDICATE, "mal": str(mal_id)},
    )


async def discover(session: AsyncSession, *, limit: int | None = None) -> Discovery:
    """Read-only walk; ``limit`` bounds records examined, not rows stepped over."""
    result = Discovery()
    redirects = await redirect_map(session)
    for row in await mal_representations(session):
        if limit is not None and result.examined >= limit:
            break
        if resolve_with(redirects, row.entity_id) != row.entity_id:
            result.skipped_redirected += 1
            continue
        result.mal_entities += 1
        result.examined += 1
        try:
            mal_id = int(row.external_id)
        except (TypeError, ValueError):
            continue
        for anilist in await anilist_entities_for_mal_id(session, mal_id):
            result.anilist_matches += 1
            root_id = resolve_with(redirects, anilist.id)
            if root_id == row.entity_id:
                result.skipped_redirected += 1
                continue
            result.pairs.append((row.entity_id, root_id, mal_id))
    return result


OFFICIAL_POLICY = "official-mal-anilist-id-v1"
BIND = "bind"
ABSTAIN = "abstain"


async def _work_types(session: AsyncSession, ids: list[Any]) -> set[str]:
    rows = await fetch(
        session,
        "SELECT DISTINCT work_type FROM work WHERE entity_id = ANY(:ids)",
        {"ids": ids},
    )
    return {row.work_type for row in rows}


async def _premieres_conflict(session: AsyncSession, left: Any, right: Any) -> bool:
    """A remake is not a duplicate: the same title a generation apart is a new work."""
    rows = await fetch(
        session,
        """
        SELECT premiered_on FROM anime_profile
        WHERE work_id = ANY(:ids) AND premiered_on IS NOT NULL
        ORDER BY premiered_on
        """,
        {"ids": [left, right]},
    )
    if len(rows) < 2:
        return False
    gap: int = abs(rows[0].premiered_on.year - rows[1].premiered_on.year)
    return gap > 1


async def _outcome(session: AsyncSession, left: Any, right: Any) -> str:
    types = await _work_types(session, [left, right])
    if types - {"anime"}:
        return ABSTAIN
    if await _premieres_conflict(session, left, right):
        return ABSTAIN
    return BIND


async def _ensure_candidate(
    session: AsyncSession, *, left: Any, right: Any, mal_id: int, create: bool
) -> tuple[Any, bool]:
    a, b = sorted((left, right), key=str)
    rows = await fetch(
        session,
        "SELECT id, status FROM match_candidate WHERE left_entity_id = :a"
        " AND right_entity_id = :b AND policy_version = :policy",
        {"a": a, "b": b, "policy": OFFICIAL_POLICY},
    )
    if rows:
        return rows[0], False
    if not create:
        return None, False
    created = await fetch(
        session,
        """
        INSERT INTO match_candidate
          (id, left_entity_id, right_entity_id, score, runner_up_margin,
           policy_version, status, hard_conflicts, created_at, updated_at)
        VALUES (gen_random_uuid(), :a, :b, 1.0000, 1.0000, :policy, 'pending',
                '[]'::jsonb, now(), now())
        RETURNING id, status
        """,
        {"a": a, "b": b, "policy": OFFICIAL_POLICY},
    )
    candidate = created[0]
    await fetch(
        session,
        """
        INSERT INTO match_evidence
          (candidate_id, evidence_type, value, weight, created_at, updated_at)
        VALUES (:candidate, 'official_external_id', CAST(:value AS jsonb), 1.0000,
                now(), now())
        RETURNING id
        """,
        {
            "candidate": candidate.id,
            "value": json.dumps({"provider_pair": "mal:anilist", "external_id": mal_id}),
        },
    )
    return candidate, True


async def bind(
    session: AsyncSession,
    *,
    create: bool = True,
    apply: bool = True,
    limit: int | None = None,
    decided_by: str = "official_mal_id",
) -> dict[str, int]:
    """The binding half. Callers decide whether to commit: the verification path does not."""
    from api.contexts.index import resolution

    result = await discover(session, limit=limit)
    summary = dict(result.summary())
    summary.update({"candidates_created": 0, "candidates_existing": 0, "bound": 0, "abstained": 0})
    for left, right, mal_id in result.pairs:
        if left == right:
            continue
        candidate, created = await _ensure_candidate(
            session, left=left, right=right, mal_id=mal_id, create=create
        )
        if candidate is None:
            continue
        summary["candidates_created" if created else "candidates_existing"] += 1
        if not apply:
            continue
        if candidate.status != "pending":
            continue
        outcome = await _outcome(session, left, right)
        reason = (
            f"AniList explicitly references MAL {mal_id} for the same anime."
            if outcome == BIND
            else "Official MAL id conflicts with entity granularity."
        )
        try:
            await resolution.decide(
                session,
                candidate_id=candidate.id,
                outcome=outcome,
                reason=reason,
                decided_by=decided_by,
            )
        except resolution.ResolutionError:
            await resolution.decide(
                session,
                candidate_id=candidate.id,
                outcome="abstain",
                reason="Official MAL id could not be bound safely.",
                decided_by=decided_by,
            )
            summary["abstained"] += 1
            continue
        summary["bound" if outcome == BIND else "abstained"] += 1
    return summary


__all__ = [
    "ANILIST_ID_MAL_PREDICATE",
    "Discovery",
    "anilist_entities_for_mal_id",
    "bind",
    "discover",
    "mal_representations",
    "redirect_map",
    "resolve_with",
]
