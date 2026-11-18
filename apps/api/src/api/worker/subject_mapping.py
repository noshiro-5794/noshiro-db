"""Mapping a Bangumi subject payload onto the fields the importer writes.

Every rule here is copied from the Django mapper, including the ones that look arbitrary,
because the two implementations have to agree on what a subject *is* before the write path
can be compared:

* ``type`` 1 is a book, split into novel/manga by the platform string; 4 is a game, and a
  ``galgame`` tag promotes it; 2 is anime, 3 music, anything else ``other``.
* fields that are present but of the wrong type are treated as absent rather than coerced.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from api.contexts.synchronization.terms import normalize_key as normalize_key

GALGAME_TAG = "galgame"


def clean_string(value: Any, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    return cleaned[:max_length] if max_length is not None else cleaned


def subject_type(data: dict[str, Any]) -> str:
    type_id = data.get("type")
    if not isinstance(type_id, int) or isinstance(type_id, bool):
        return "other"
    if type_id == 1:
        platform = data.get("platform")
        if isinstance(platform, str):
            if "小说" in platform:
                return "novel"
            if "漫画" in platform:
                return "manga"
        return "book"
    if type_id == 2:
        return "anime"
    if type_id == 3:
        return "music"
    if type_id == 4:
        return "galgame" if GALGAME_TAG in [tag.lower() for tag in meta_tags(data)] else "game"
    return "other"


def meta_tags(data: dict[str, Any]) -> list[str]:
    tags = data.get("meta_tags")
    if tags is None:
        tags = data.get("metatag")
    if not isinstance(tags, list):
        return []
    return [tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()]


def subject_date(data: dict[str, Any]) -> date | None:
    value = clean_string(data.get("date"))
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def image_urls(data: dict[str, Any]) -> tuple[str, str]:
    images = data.get("images")
    if not isinstance(images, dict):
        return "", ""
    return (
        clean_string(images.get("large"), max_length=1024),
        clean_string(images.get("medium"), max_length=1024),
    )


def infobox_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("infobox")
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        normalized_key = key.strip() if isinstance(key, str) else ""
        normalized_value = _infobox_value(item.get("value"))
        if not normalized_key and not normalized_value:
            continue
        entries.append({"key": normalized_key, "value": normalized_value})
    return entries


def _infobox_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()]
    if isinstance(value, list):
        return [
            item["v"].strip()
            for item in value
            if isinstance(item, dict) and isinstance(item.get("v"), str)
        ]
    return []


def tag_names(data: dict[str, Any]) -> list[str]:
    return meta_tags(data)


def map_subject(data: dict[str, Any]) -> dict[str, Any]:
    """The mapped shape the write primitives consume."""
    large, medium = image_urls(data)
    return {
        "subject_type": subject_type(data),
        "title": clean_string(data.get("name"), max_length=256),
        "title_cn": clean_string(data.get("name_cn"), max_length=256),
        "date": subject_date(data),
        "image_original": large,
        "image_thumbnail": medium,
        "platform": clean_string(data.get("platform"))[:256],
        "description": clean_string(data.get("summary")),
        "nsfw": data.get("nsfw") if isinstance(data.get("nsfw"), bool) else False,
        "series": data.get("series") if isinstance(data.get("series"), bool) else False,
        "volumes": data.get("volumes") if isinstance(data.get("volumes"), int) else None,
        "eps": data.get("eps") if isinstance(data.get("eps"), int) else None,
        "total_episodes": data.get("total_episodes")
        if isinstance(data.get("total_episodes"), int)
        else None,
        "infobox": infobox_entries(data),
        "tags": tag_names(data),
    }


__all__ = [
    "GALGAME_TAG",
    "clean_string",
    "image_urls",
    "infobox_entries",
    "map_subject",
    "meta_tags",
    "normalize_key",
    "subject_date",
    "subject_type",
    "tag_names",
    "work_facts",
]


def work_facts(mapped: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    """The facts a mapped subject contributes, as ``slug -> (value, value_type)``.

    Booleans and numbers keep their type; a string is a date only for ``release-date``,
    because a date stored as text would sort with the strings instead of the dates.
    """
    release = mapped.get("date")
    candidates: dict[str, Any] = {
        "release-date": release.isoformat() if release else None,
        "platform": mapped.get("platform") or None,
        "series": mapped.get("series"),
        "volumes": mapped.get("volumes"),
        "episode-count": mapped.get("total_episodes") or mapped.get("eps"),
        "provider-infobox": mapped.get("infobox") or None,
        "provider-tags": mapped.get("tags") or None,
    }
    out: dict[str, tuple[Any, str]] = {}
    for slug, value in candidates.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, int | float):
            value_type = "number"
        elif isinstance(value, str):
            value_type = "date" if slug == "release-date" else "string"
        else:
            value_type = "json"
        out[slug] = (value, value_type)
    return out
