"""Priority for eligible provider evidence in relationship read models."""

from typing import Literal

from api.config import settings

RelationshipKind = Literal["episodes", "credits", "relations"]


def priority(kind: RelationshipKind, provider: str | None) -> tuple[int, str]:
    order: tuple[str, ...] = getattr(settings.relationship_sources, kind)
    if provider is None:
        return len(order) + 1, ""
    if provider in order:
        return order.index(provider), provider
    return len(order), provider
