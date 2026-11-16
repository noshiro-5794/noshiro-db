"""Source relationship vocabularies mapped to canonical relation names."""

from api.shared.text import slugify

RELATION_TYPES = {
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
    "SEQUEL": "sequel",
    "PREQUEL": "prequel",
    "ADAPTATION": "adaptation",
    "ALTERNATIVE": "alternate-version",
    "SPIN_OFF": "side-story",
    "SIDE_STORY": "side-story",
    "PARENT": "parent-story",
    "CHARACTERS": "shares-characters",
    "SUMMARY": "summary",
    "FULL_STORY": "full-story",
    "OTHER": "related",
    "续作": "sequel",
    "前传": "prequel",
    "改编": "adaptation",
    "衍生": "side-story",
    "番外": "side-story",
    "总集篇": "summary",
    "相关": "related",
}


def canonical_relation_type(value: str) -> str:
    raw = value.strip()
    return RELATION_TYPES.get(raw.upper(), RELATION_TYPES.get(raw, slugify(raw)[:128] or "related"))
