"""Priority for eligible provider evidence in relationship read models."""

from typing import Literal
from unicodedata import normalize

from api.config import settings

RelationshipKind = Literal["episodes", "credits", "relations"]


def priority(kind: RelationshipKind, provider: str | None) -> tuple[int, str]:
    order: tuple[str, ...] = getattr(settings.relationship_sources, kind)
    if provider is None:
        return len(order) + 1, ""
    if provider in order:
        return order.index(provider), provider
    return len(order), provider


ROLE_ALIASES = {
    "导演": "director",
    "監督": "director",
    "原作": "original creator",
    "脚本": "script",
    "編劇": "script",
    "编剧": "script",
    "系列构成": "series composition",
    "シリーズ構成": "series composition",
    "角色设计": "character design",
    "キャラクターデザイン": "character design",
    "音乐": "music",
    "音楽": "music",
}


def role_key(role: str) -> str:
    key = " ".join(normalize("NFKC", role).casefold().split())
    return ROLE_ALIASES.get(key, key)
