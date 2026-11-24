"""Typed facts and attributed infobox entries available to work presentation."""

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from unicodedata import normalize
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.identity.roles import ROLE_NAMES, role_key, role_label
from api.db import fetch
from api.integrations.providers.vndb_vocabulary import PLATFORM_LABELS

MAX_FIELDS = 120
DETAILED_WORK_TYPES = {"anime", "galgame"}
DAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
ORDER = (
    "format",
    "release-date",
    "end-date",
    "episodes",
    "broadcast-day",
    "broadcast-time",
    "broadcast-timezone",
    "season",
    "status",
    "duration-minutes",
    "source-material",
    "animation-production",
    "developer",
    "platforms",
    "languages",
    "genres",
    "themes",
    "demographics",
    "content-classification",
)
FACT_KEYS = {
    "mal-type": "format",
    "anilist-format": "format",
    "episode-count": "episodes",
    "mal-season": "season",
    "anilist-season": "season",
    "mal-status": "status",
    "anilist-status": "status",
    **{key: key for key in ORDER if key not in {"format", "episodes", "season", "status"}},
    "platform": "platform",
    "mal-source": "source-material",
    "anilist-source": "source-material",
    "mal-studios": "animation-production",
    "mal-rating": "content-classification",
    "mal-genres": "genres",
    "mal-themes": "themes",
    "mal-demographics": "demographics",
    "anilist-genres": "genres",
    "anilist-country": "country",
    "anilist-hashtag": "hashtag",
    "anilist-producers": "producers",
    "anilist-studios": "animation-production",
    "anilist-next-broadcast": "next-broadcast",
    "mal-year": "season-year",
    "anilist-season-year": "season-year",
    "release-period": "release-date",
    "vndb-status": "status",
    "vndb-original-language": "original-language",
    "vndb-length": "estimated-length",
    "vndb-developers": "developer",
}
INFOBOX_KEYS = {
    "话数": "episodes",
    "話数": "episodes",
    "放送开始": "release-date",
    "放送開始": "release-date",
    "播放结束": "end-date",
    "放送星期": "broadcast-day",
    "放送时间": "broadcast-time",
    "放送時間": "broadcast-time",
    "时区": "broadcast-timezone",
    "季节": "season",
    "播出状态": "status",
    "播放电视台": "broadcaster",
    "电视台": "broadcaster",
    "官方网站": "website",
    "动画制作": "animation-production",
    "集数": "episodes",
    "发行日期": "release-date",
    "发售日期": "release-date",
    "發售日期": "release-date",
    "平台": "platforms",
    "开发": "developer",
    "開発": "developer",
    "发行": "publisher",
    "發行": "publisher",
    "游戏类型": "genres",
    "游戏引擎": "game-engine",
    "人物设定": "infobox:character design",
    "劇本": "infobox:scenario",
    "剧本": "infobox:scenario",
    "游玩人数": "players",
    "国家/地区": "country",
    "语言": "languages",
    "アニメーション制作": "animation-production",
}
HIDDEN_LABEL = re.compile(
    r"(评分|評分|评分人数|評價|评价|排名|投票|人气|人氣|热度|熱度|收藏|在看|观看人数|評論|评论|"
    r"別名|别名|中文名|原名|score|rating|votes?|popularity|rank|watchers|favorites|members)",
    re.I,
)
WEEKDAYS = dict(
    zip(
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
        ("mon", "tue", "wed", "thu", "fri", "sat", "sun"),
        strict=True,
    )
)
for prefix, suffixes in (
    ("星期", "一二三四五六日"),
    ("周", "一二三四五六日"),
    ("", "月火水木金土日"),
):
    for suffix, weekday in zip(suffixes, DAY_CODES, strict=True):
        WEEKDAYS[f"{prefix}{suffix}" + ("曜日" if not prefix else "")] = weekday


PLACEHOLDERS = {"-", "—", "?", "n/a", "none", "unknown", "暂无", "不明", "未知"}
AMBIGUOUS_LABELS = {
    "信息",
    "其他",
    "链接",
    "link",
    "misc",
    "other",
    "unknown",
    "备注",
    "note",
    "标签",
    "tags",
}
TITLE_LABELS = {"原名", "原题", "标题", "title", "alternative titles", "synonyms"}
RECOGNIZED_INFOBOX_LABELS = {
    "3DCG 导演",
    "Artwork",
    "Character design",
    "Copyright",
    "Director",
    "Editing",
    "Music",
    "OP・ED 分镜",
    "OP・ED 演出",
    "Production staff",
    "Quality assurance",
    "Scenario",
    "Songs",
    "Translation",
    "Translation editions",
    "主题歌作曲",
    "主题歌作词",
    "主题歌演出",
    "主题歌编曲",
    "人物设定",
    "企画",
    "作画监督",
    "作画监督助理",
    "其他版本",
    "分镜",
    "制作人",
    "制作管理",
    "制作统括",
    "制作进行",
    "制片人",
    "剧中剧分镜演出",
    "剧本",
    "剪辑",
    "副制片人",
    "副导演",
    "动作作画监督",
    "动画制作",
    "动画制片人",
    "协力",
    "原作",
    "原画",
    "发行",
    "发行日期",
    "售价",
    "在线剪辑",
    "声优",
    "官方网站",
    "宣传制片人",
    "导演",
    "平台",
    "开发",
    "录音",
    "录音助理",
    "录音工作室",
    "总作画监督",
    "总制片人",
    "执行制片人",
    "插入歌演出",
    "插画",
    "摄影监督",
    "摄影监督助理",
    "播放电视台",
    "放送星期",
    "构图",
    "概念艺术",
    "游戏引擎",
    "游戏类型",
    "游玩人数",
    "演出",
    "演出助理",
    "特效",
    "系列构成",
    "编剧",
    "美术",
    "美术监督",
    "美术设计",
    "脚本",
    "色彩脚本",
    "色彩设计",
    "製作",
    "设定",
    "设定制作",
    "音乐",
    "音乐制作",
    "音乐制作人",
    "音乐助理",
    "音乐监督",
    "音响",
    "音响监督",
}


class FieldChoice(BaseModel):
    evidence_id: str = Field(pattern=r"^[0-9a-f-]{36}:[0-9a-f-]{36}:-?\d+$")
    label: str = Field(min_length=1, max_length=80)


def normalize_value(key: str, text: str) -> str:
    if key in {"release-date", "end-date"} and (
        match := re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    ):
        year, month, day = map(int, match.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"
    if key == "broadcast-day":
        return WEEKDAYS.get(text.casefold(), text)
    if key == "content-classification":
        return text.replace("_", "-").upper()
    if key == "estimated-length":
        return {
            "1": "under 2 hours",
            "2": "2-10 hours",
            "3": "10-30 hours",
            "4": "30-50 hours",
            "5": "over 50 hours",
        }.get(text, text)
    if key in {"format", "season", "status"}:
        value = text.lower().replace(" ", "_")
        return {
            "releasing": "airing",
            "currently_airing": "airing",
            "finished_airing": "finished",
            "not_yet_aired": "upcoming",
            "not_yet_released": "upcoming",
        }.get(value, value)
    return text


def _candidate(
    row: Any, index: int, label: str, raw_values: Any, key: str
) -> dict[str, Any] | None:
    if key == "release-date" and isinstance(raw_values, dict):
        raw_values = raw_values.get("raw_value")
    if key == "next-broadcast" and isinstance(raw_values, dict):
        airing = raw_values.get("airing_at")
        if not isinstance(airing, int) or airing <= datetime.now(UTC).timestamp():
            return None
        raw_values = [f"#{raw_values['episode']}", datetime.fromtimestamp(airing, UTC).isoformat()]
    if not isinstance(raw_values, list):
        raw_values = [raw_values]
    if row.provider == "vndb" and key == "platforms":
        raw_values = [
            PLATFORM_LABELS[value]
            for value in raw_values
            if isinstance(value, str) and value in PLATFORM_LABELS and value != "oth"
        ]
    values = list(
        dict.fromkeys(
            normalize_value(key, str(value).strip())
            for value in raw_values
            if isinstance(value, str | int | float)
            and not isinstance(value, bool)
            and str(value).strip().casefold() not in PLACEHOLDERS | {""}
        )
    )
    if not values:
        return None
    # Preserve entire scoped credit strings instead of splitting on punctuation.
    if sum(map(len, values)) > 3500:
        return None
    if index == -1 and label == key:
        label = {
            "duration-minutes": "Episode duration (minutes)",
            "content-classification": "Content classification",
            "next-broadcast": "Next episode",
        }.get(key, key.replace("-", " ").capitalize())
    return {
        "id": f"{row.fact_id}:{row.observation_id}:{index}",
        "key": key,
        "label": label[:80],
        "values": values,
        "provider": row.provider,
        "ai_allowed": row.ai_allowed,
    }


async def candidates(
    session: AsyncSession, members: list[str], *, for_ai: bool
) -> list[dict[str, Any]]:
    rows = await fetch(
        session,
        """
        SELECT DISTINCT ON (fact.id, provider.slug)
               fact.id AS fact_id, predicate.slug, fact.value,
               observation.id AS observation_id, provider.slug AS provider,
               provider.ai_usage_policy = 'allowed' AS ai_allowed
        FROM fact
        JOIN predicate ON predicate.id = fact.predicate_id
        JOIN fact_evidence AS evidence ON evidence.fact_id = fact.id
        JOIN provider_observation AS observation ON observation.id = evidence.observation_id
        JOIN provider_current_observation AS pointer ON pointer.observation_id = observation.id
          AND pointer.provider_record_id = observation.provider_record_id
        JOIN provider_record AS record ON record.id = observation.provider_record_id
        JOIN provider_namespace AS namespace ON namespace.id = record.namespace_id
        JOIN provider ON provider.id = namespace.provider_id
        WHERE fact.entity_id = ANY(CAST(:members AS uuid[]))
          AND predicate.slug = ANY(CAST(:slugs AS text[]))
          AND fact.status <> 'rejected' AND NOT fact.is_machine_generated
          AND fact.safety NOT IN ('suggestive','explicit') AND fact.spoiler_level = 0
          AND record.status = 'active' AND provider.redistribution_policy <> 'forbidden'
          AND (NOT :for_ai OR provider.ai_usage_policy = 'allowed')
        ORDER BY fact.id, provider.slug, observation.observed_at DESC, observation.id
        """,
        {"members": members, "slugs": [*FACT_KEYS, "provider-infobox"], "for_ai": for_ai},
    )
    output = []
    for row in rows:
        if row.slug == "provider-infobox":
            for index, entry in enumerate(row.value if isinstance(row.value, list) else []):
                if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
                    continue
                label = normalize("NFKC", entry["key"]).strip()
                if (
                    0 < len(label) <= 80
                    and any(character.isalpha() for character in label)
                    and label.casefold() not in AMBIGUOUS_LABELS | TITLE_LABELS
                    and not HIDDEN_LABEL.search(label)
                ):
                    key = INFOBOX_KEYS.get(label, "infobox:" + role_key(label))
                    item = _candidate(row, index, label, entry.get("value"), key)
                    if item:
                        output.append(item)
        else:
            key = FACT_KEYS[row.slug]
            if (for_ai and key == "next-broadcast") or (
                key == "platform" and row.value in ("游戏", "動畫", "动画")
            ):
                continue
            if (
                key == "platform"
                and isinstance(row.value, str)
                and row.value.lower() in {"tv", "ova", "ona", "movie", "special"}
            ):
                key = "format"
            item = _candidate(row, -1, key, row.value, key)
            if item:
                output.append(item)
    return sorted(
        output,
        key=lambda item: (
            ORDER.index(item["key"]) if item["key"] in ORDER else len(ORDER),
            item["provider"] != "bangumi",
            item["id"],
        ),
    )[: MAX_FIELDS * 2]


def evidence_hash(candidate: dict[str, Any]) -> str:
    content = [candidate["key"], candidate["label"], candidate["values"]]
    return sha256(json.dumps(content, ensure_ascii=False).encode()).hexdigest()


async def save_choices(
    session: AsyncSession, revision_id: int, choices: list[FieldChoice], evidence: dict[str, Any]
) -> None:
    if not choices:
        return
    rows = []
    for position, choice in enumerate(choices):
        candidate = evidence[choice.evidence_id]
        fact, observation, index = choice.evidence_id.split(":")
        rows.append(
            {
                "field_key": candidate["key"],
                "label": choice.label.strip(),
                "position": position,
                "fact_id": str(UUID(fact)),
                "observation_id": str(UUID(observation)),
                "item_index": int(index),
                "evidence_hash": evidence_hash(candidate),
            }
        )
    await fetch(
        session,
        """
        INSERT INTO entity_metadata_field_choice
          (revision_id, field_key, label, position, fact_id, observation_id,
           item_index, evidence_hash)
        SELECT :id, choice.*
        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS choice(
          field_key text, label text, position smallint, fact_id uuid, observation_id uuid,
          item_index integer, evidence_hash text
        )
        RETURNING position
        """,
        {"id": revision_id, "rows": json.dumps(rows, ensure_ascii=False)},
    )


async def render(
    session: AsyncSession,
    members: list[str],
    revision_id: int | None,
    *,
    machine: bool,
    language: str,
) -> list[dict[str, Any]]:
    options = await candidates(session, members, for_ai=False)
    by_id = {item["id"]: item for item in options}
    by_key: dict[str, dict[str, Any]] = {}
    if revision_id is not None:
        for row in await fetch(
            session,
            """
            SELECT * FROM entity_metadata_field_choice WHERE revision_id = :id ORDER BY position
            """,
            {"id": revision_id},
        ):
            item = by_id.get(f"{row.fact_id}:{row.observation_id}:{row.item_index}")
            if (
                item
                and (not machine or item["ai_allowed"])
                and row.evidence_hash == evidence_hash(item)
            ):
                by_key[row.field_key] = {**item, "label": row.label}
    for item in options:
        if not item["key"].startswith("infobox:"):
            by_key.setdefault(item["key"], item)
        elif item["label"] in RECOGNIZED_INFOBOX_LABELS or role_key(item["label"]) in ROLE_NAMES:
            by_key.setdefault(item["key"], {**item, "label": role_label(item["label"], language)})
    return [
        {key: item[key] for key in ("key", "label", "values", "provider")}
        for item in list(by_key.values())[:MAX_FIELDS]
    ]
