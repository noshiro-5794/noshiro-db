"""Which kinds of work may be bound to each other across providers.

A merge claims that two provider records describe the same real work, so it is
only meaningful inside a family: an anime is the same work as another provider's
anime, and a galgame is the same work as another provider's galgame - which some
providers file under the broader ``game`` type.

Everything else is deliberately out of scope. Characters, episodes, releases and
contributors are per-provider records whose identity follows their parent work;
binding them across providers would claim a correspondence the evidence does not
support, and the catalogue only ever projects works.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.index.models import Work

WORK = Work.WorkType

# Types that may take part in cross-provider identity at all.
MATCHABLE_WORK_TYPES = frozenset({WORK.ANIME, WORK.GALGAME})

# Types a type may be bound to, itself included. ``game`` is the broader Bangumi
# type that holds galgames alongside other games, so a galgame may bind to it;
# two ``game`` works may also be the same game.
_BINDABLE_WITH: dict[str, frozenset[str]] = {
    WORK.ANIME: frozenset({WORK.ANIME}),
    WORK.GALGAME: frozenset({WORK.GALGAME, WORK.GAME}),
    WORK.GAME: frozenset({WORK.GALGAME, WORK.GAME}),
}

# The types a provider's search should look for when its own work is of this
# type, used to narrow target blocking to the family instead of the catalogue.
_SEARCHABLE_TARGETS: dict[str, frozenset[str]] = {
    WORK.ANIME: frozenset({WORK.ANIME}),
    WORK.GALGAME: frozenset({WORK.GALGAME}),
    WORK.GAME: frozenset({WORK.GALGAME, WORK.GAME}),
}


def target_types_for(work_type: str) -> frozenset[str]:
    """Work types worth searching for a given source work type."""
    return _SEARCHABLE_TARGETS.get(work_type, frozenset())


def are_bindable(left_types: Iterable[str], right_types: Iterable[str]) -> bool:
    """Whether two sets of work types may be merged into one canonical work."""
    left = {value for value in left_types if value}
    right = {value for value in right_types if value}
    if not left or not right:
        return False
    return any(
        other in _BINDABLE_WITH.get(work_type, frozenset())
        for work_type in left
        for other in right
    )


def is_matchable(work_type: str) -> bool:
    return work_type in MATCHABLE_WORK_TYPES


__all__ = [
    "MATCHABLE_WORK_TYPES",
    "are_bindable",
    "is_matchable",
    "target_types_for",
]
