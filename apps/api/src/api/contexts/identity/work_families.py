"""Work families eligible for cross-provider identity binding."""

from collections.abc import Iterable

BINDABLE = {
    "anime": frozenset({"anime"}),
    "galgame": frozenset({"galgame", "game"}),
    "game": frozenset({"galgame", "game"}),
}


def are_bindable(left: Iterable[str], right: Iterable[str]) -> bool:
    right_types = set(right)
    return any(other in BINDABLE.get(kind, frozenset()) for kind in left for other in right_types)
