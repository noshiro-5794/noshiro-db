"""Which MAL records have an official AniList twin, and can be bound.

The reconciliation has two halves. This module implements the **discovery** half only:
walk the active MAL representations in id order, resolve them through the redirect graph,
and look up the AniList entity that carries the matching ``anilist-id-mal`` fact. It writes
nothing, so it can be compared against the Django service on a live database.

The binding half (candidates, decisions, merges) is deliberately absent until the
discovery half matches, because a mismatch there would silently merge the wrong pairs.
"""

from __future__ import annotations

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


__all__ = [
    "ANILIST_ID_MAL_PREDICATE",
    "Discovery",
    "anilist_entities_for_mal_id",
    "discover",
    "mal_representations",
    "redirect_map",
    "resolve_with",
]
