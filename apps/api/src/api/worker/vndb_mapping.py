"""Pure VNDB mappings for names, partial dates, media and source facts."""

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from api.contexts.identity.names import SourceName


@dataclass(frozen=True, slots=True)
class Fact:
    slug: str
    name: str
    value: Any
    value_type: str
    json_pointer: str
    spoiler_level: int = 0


VNDB_STAFF_LABELS = {
    "scenario": "Scenario",
    "director": "Director",
    "chardesign": "Character design",
    "art": "Artwork",
    "music": "Music",
    "songs": "Songs",
    "translator": "Translation",
    "editor": "Editing",
    "qa": "Quality assurance",
    "staff": "Production staff",
}


def simple_names(data: dict[str, Any]) -> list[SourceName]:
    names = []
    for key, kind, original in (
        ("title", "official", False),
        ("name", "official", False),
        ("alttitle", "original", True),
        ("original", "original", True),
    ):
        value = data.get(key)
        if isinstance(value, str) and value:
            names.append(
                SourceName(
                    value, data.get("olang") or data.get("lang") or "", kind, original, not original
                )
            )
    return names


def work_names(data: dict[str, Any]) -> list[SourceName]:
    names = []
    for item in data.get("titles") or []:
        title = item.get("title")
        if not isinstance(title, str) or not title:
            continue
        language = item.get("lang") or ""
        original = language == (data.get("olang") or "")
        names.append(
            SourceName(
                title,
                language,
                "original" if original else "official",
                original,
                bool(item.get("official")),
            )
        )
        latin = item.get("latin")
        if isinstance(latin, str) and latin and latin != title:
            names.append(SourceName(latin, language, "romanized"))
    names.extend(
        SourceName(alias, "", "alias")
        for alias in data.get("aliases") or []
        if isinstance(alias, str) and alias
    )
    names.extend(
        name
        for name in simple_names(data)
        if not name.is_original or not any(original.is_original for original in names)
    )
    return names


def positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def partial_date(value: Any) -> tuple[date | None, date | None, str]:
    if not isinstance(value, str) or not value or value.upper() == "TBA":
        return None, None, "unknown"
    parts = value.split("-")
    try:
        if len(parts) == 1 and len(parts[0]) == 4:
            year = int(parts[0])
            return date(year, 1, 1), date(year, 12, 31), "year"
        if len(parts) == 2:
            year, month = (int(part) for part in parts)
            return date(year, month, 1), date(year, month, monthrange(year, month)[1]), "month"
        parsed = date.fromisoformat(value)
        return parsed, parsed, "day"
    except (TypeError, ValueError):
        return None, None, "unknown"


def media_safety(data: dict[str, Any]) -> str:
    sexual = data.get("sexual")
    if not isinstance(sexual, (int, float)):
        return "unknown"
    if sexual >= 1.5:
        return "explicit"
    if sexual > 0:
        return "suggestive"
    return "safe"


def audience(data: dict[str, Any]) -> str:
    return "adult" if media_safety(data.get("image") or {}) == "explicit" else "unknown"


def development_status(value: Any) -> str:
    return {0: "finished", 1: "in-development", 2: "cancelled"}.get(value, "")


def spoiler_level(value: Any) -> int:
    return min(max(value, 0), 3) if isinstance(value, int) else 0


def credited_name(data: dict[str, Any]) -> str:
    for key in ("name", "title", "original"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value[:512]
    return ""


def relation_type(value: str | None) -> str:
    return {
        "seq": "sequel",
        "preq": "prequel",
        "set": "same-setting",
        "alt": "alternate-version",
        "char": "shares-characters",
        "side": "side-story",
        "par": "parent-story",
        "ser": "same-series",
        "fan": "fandisc",
        "orig": "original-version",
    }.get(value or "", "related")


def release_work_role(value: str | None) -> str:
    return {"complete": "primary", "partial": "included", "trial": "bonus"}.get(
        value or "", "primary"
    )


def _optional_fact(
    data: dict[str, Any], field: str, slug: str, name: str, value_type: str
) -> list[Fact]:
    value = data.get(field)
    if value is None or value == "" or value == [] or value == {}:
        return []
    return [Fact(slug, name, value, value_type, f"/{field}")]


def _credit_fields(data: dict[str, Any]) -> list[Fact]:
    editions = {
        item["eid"]: item["name"]
        for item in data.get("editions") or []
        if isinstance(item, dict)
        and isinstance(item.get("eid"), int)
        and isinstance(item.get("name"), str)
        and item["name"].strip()
    }
    credits = defaultdict(list)
    for item in data.get("staff") or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        name = item.get("original") or item.get("name")
        if not isinstance(role, str) or not isinstance(name, str) or not role or not name:
            continue
        qualifiers = [
            part
            for part in (editions.get(item.get("eid")), item.get("note"))
            if isinstance(part, str) and part.strip()
        ]
        qualifier = " · ".join(qualifiers)
        credits[role].append(f"{name} ({qualifier})" if qualifier else name)
    fields = [
        {"key": VNDB_STAFF_LABELS[role], "value": list(dict.fromkeys(values))}
        for role, values in credits.items()
        if role in VNDB_STAFF_LABELS
    ]
    if editions:
        fields.append({"key": "Translation editions", "value": list(editions.values())})
    return (
        [Fact("provider-infobox", "Provider infobox", fields, "json", "/staff")] if fields else []
    )


def work_facts(data: dict[str, Any]) -> list[Fact]:
    facts = []
    if data.get("released"):
        start, end, precision = partial_date(data["released"])
        facts.append(
            Fact(
                "release-period",
                "Release Period",
                {
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "precision": precision,
                    "raw_value": data["released"],
                },
                "json",
                "/released",
            )
        )
    for field, slug, name, value_type in (
        ("languages", "languages", "Languages", "json"),
        ("platforms", "platforms", "Platforms", "json"),
    ):
        facts.extend(_optional_fact(data, field, slug, name, value_type))
    for field, slug, label in (
        ("olang", "vndb-original-language", "Original language"),
        ("length", "vndb-length", "Estimated length"),
    ):
        facts.extend(
            _optional_fact(data, field, slug, label, "string" if field == "olang" else "number")
        )
    if status := development_status(data.get("devstatus")):
        facts.append(Fact("vndb-status", "Development status", status, "string", "/devstatus"))
    for field, slug, label in (("developers", "vndb-developers", "Development"),):
        names = [
            item.get("original") or item.get("name")
            for item in data.get(field) or []
            if isinstance(item, dict) and not item.get("spoiler") and not item.get("lie")
        ]
        if names:
            facts.append(Fact(slug, label, names, "json", "/" + field))
    facts.extend(_credit_fields(data))
    return facts


def release_facts(data: dict[str, Any]) -> list[Fact]:
    facts = []
    for field in ("languages", "media", "voiced", "engine", "freeware", "uncensored"):
        value = data.get(field)
        if isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            value_type = "number"
        elif isinstance(value, str):
            value_type = "string"
        else:
            value_type = "json"
        facts.extend(
            _optional_fact(
                data,
                field,
                f"release-{field}",
                f"Release {field.replace('_', ' ').title()}",
                value_type,
            )
        )
    resolution = data.get("resolution")
    if resolution is not None and resolution != "" and resolution != []:
        value = {"value": resolution} if isinstance(resolution, str) else resolution
        facts.append(Fact("release-resolution", "Release Resolution", value, "json", "/resolution"))
    return facts


def character_facts(data: dict[str, Any]) -> list[Fact]:
    facts = []
    for field in (
        "blood_type",
        "height",
        "weight",
        "bust",
        "waist",
        "hips",
        "cup",
        "birthday",
        "age",
    ):
        value = data.get(field)
        value_type = "json"
        if isinstance(value, (int, float)):
            value_type = "number"
        elif isinstance(value, str):
            value_type = "string"
        facts.extend(
            _optional_fact(
                data,
                field,
                f"character-{field}",
                f"Character {field.replace('_', ' ').title()}",
                value_type,
            )
        )
    for field in ("sex", "gender"):
        values = data.get(field)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values[:2]):
            if value is not None:
                facts.append(
                    Fact(
                        f"character-{'actual-' if index else ''}{field}",
                        f"Character {'Actual ' if index else ''}{field.title()}",
                        value,
                        "string",
                        f"/{field}/{index}",
                        2 if index else 0,
                    )
                )
    return facts
