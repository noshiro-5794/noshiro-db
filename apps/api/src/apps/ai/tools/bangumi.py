"""Bangumi catalog search for the AI harness.

The tool is read-only and delegates to Bangumi's v0 search endpoint through the
existing provider client so proxy, rate-limit, and provider-policy rules stay
in one place. Results are intentionally compact: the AI uses them to decide
whether a canonical work already exists locally or must be imported first.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.sync.providers.bangumi import BangumiAPIError, BangumiClient

from .registry import ToolDefinition, ToolInput, ToolOutput, ToolRegistry


class BangumiSearchInput(ToolInput):
    keyword: str = Field(min_length=1, max_length=512)
    limit: int = Field(default=5, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class BangumiSearchOutput(ToolOutput):
    available: bool
    reason: str = ""
    total: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)


class BangumiSearchTool:
    """Search anime subjects on Bangumi through the official v0 endpoint."""

    name = "bangumi.search_subjects"
    version = "1.0.0"

    def __init__(self, client: BangumiClient | None = None) -> None:
        self._client = client

    def execute(self, value: BangumiSearchInput) -> BangumiSearchOutput:
        client = self._client or BangumiClient()
        try:
            payload = client.search_subjects(
                keyword=value.keyword,
                subject_types=(2,),
                limit=value.limit,
                offset=value.offset,
            )
        except BangumiAPIError as exc:
            return BangumiSearchOutput(
                available=False,
                reason=f"{type(exc).__name__}: {exc}"[:1000],
            )
        items = payload.get("data") or []
        total = payload.get("total")
        results = [
            {
                "id": int(item["id"]),
                "name": str(item.get("name") or ""),
                "name_cn": str(item.get("name_cn") or ""),
                "date": item.get("date"),
                "summary": str(item.get("summary") or "")[:800],
                "platform": str(item.get("platform") or ""),
                "images": {
                    key: str(value)
                    for key, value in (item.get("images") or {}).items()
                    if value
                },
                "url": f"https://bgm.tv/subject/{int(item['id'])}",
            }
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        ]
        return BangumiSearchOutput(
            available=True,
            total=int(total) if isinstance(total, int) else len(results),
            results=results,
        )


bangumi_search_tool = BangumiSearchTool()


def register_bangumi_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            name=bangumi_search_tool.name,
            description=(
                "Search anime subjects on Bangumi by title; used to confirm "
                "whether a Bangumi subject exists before importing/linking."
            ),
            input_model=BangumiSearchInput,
            output_model=BangumiSearchOutput,
            handler=bangumi_search_tool.execute,
            version=bangumi_search_tool.version,
            permission="bangumi:search",
            risk_level="read_only",
            records_evidence=True,
            timeout_seconds=30,
            rate_limit_per_minute=30,
        )
    )
