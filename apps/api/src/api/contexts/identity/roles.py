"""Credit role terminology shared by the credit and work-metadata readers."""

import re
from unicodedata import normalize

# Keys are stable across locales. The source credit retains its original text.
ROLE_NAMES = {
    "director": ("导演", "監督", "Director"),
    "assistant director": ("副导演", "副監督", "Assistant Director"),
    "original creator": ("原作", "原作", "Original Creator"),
    "script": ("脚本", "脚本", "Script"),
    "series composition": ("系列构成", "シリーズ構成", "Series Composition"),
    "character design": ("人物设定", "キャラクターデザイン", "Character Design"),
    "music": ("音乐", "音楽", "Music"),
    "sound director": ("音响监督", "音響監督", "Sound Director"),
    "storyboard": ("分镜", "絵コンテ", "Storyboard"),
    "animation director": ("作画监督", "作画監督", "Animation Director"),
    "chief animation director": ("总作画监督", "総作画監督", "Chief Animation Director"),
    "art director": ("美术监督", "美術監督", "Art Director"),
    "animation production": ("动画制作", "アニメーション制作", "Animation Production"),
    "studio": ("工作室", "スタジオ", "Studio"),
    "producer": ("制片人", "プロデューサー", "Producer"),
    "staff": ("职员", "スタッフ", "Staff"),
}


def _normalized(role: str) -> str:
    return " ".join(normalize("NFKC", role).casefold().split())


ROLE_ALIASES = {
    **{_normalized(label): key for key, labels in ROLE_NAMES.items() for label in labels},
    "導演": "director",
    "副導演": "assistant director",
    "編劇": "script",
    "编剧": "script",
    "系列構成": "series composition",
    "角色设计": "character design",
    "角色設計": "character design",
    "音樂": "music",
}
LANGUAGE_INDEX = {"zh": 0, "ja": 1, "en": 2}


def role_key(role: str) -> str:
    key = _normalized(role)
    return ROLE_ALIASES.get(key, key)


def role_label(role: str, language: str) -> str:
    index = LANGUAGE_INDEX.get(language.split(";", 1)[0].strip().lower().split("-", 1)[0])
    if index is None:
        return role
    labels = ROLE_NAMES.get(role_key(role))
    if labels is not None:
        return labels[index]
    qualified = re.fullmatch(r"(.+?)(\s*[(\uff08].*)", role)
    if qualified and (labels := ROLE_NAMES.get(role_key(qualified[1]))):
        return labels[index] + qualified[2]
    return role
