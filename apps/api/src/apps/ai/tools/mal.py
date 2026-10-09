"""External MAL search tools for AI retrieval skills."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.sync.providers.mal import mal_api_client

from .registry import ToolDefinition, ToolInput, ToolOutput, ToolRegistry


class SearchMALInput(ToolInput):
    query: str = Field(min_length=1, max_length=160)
    limit: int = Field(default=10, ge=1, le=20)


class SearchMALOutput(ToolOutput):
    results: list[dict[str, Any]]


def _search_mal(value: SearchMALInput) -> SearchMALOutput:
    payload = mal_api_client.search_anime(
        query=value.query.strip()[:160],
        limit=value.limit,
    )
    results: list[dict[str, Any]] = []
    for wrapper in payload.get("data") or []:
        if not isinstance(wrapper, dict):
            continue
        node = wrapper.get("node") if isinstance(wrapper.get("node"), dict) else wrapper
        item = _compact_mal_node(node)
        if item is not None:
            results.append(item)
    return SearchMALOutput(results=results)


def _compact_mal_node(node: Any) -> dict[str, Any] | None:
    if not isinstance(node, dict) or not isinstance(node.get("id"), int):
        return None
    alternative_titles = (
        node.get("alternative_titles")
        if isinstance(node.get("alternative_titles"), dict)
        else {}
    )
    broadcast = node.get("broadcast") if isinstance(node.get("broadcast"), dict) else {}
    return {
        "id": node["id"],
        "title": node.get("title") or "",
        "alternative_titles": {
            "synonyms": alternative_titles.get("synonyms") or [],
            "en": alternative_titles.get("en") or "",
            "ja": alternative_titles.get("ja") or "",
        },
        "media_type": node.get("media_type") or "",
        "status": node.get("status") or "",
        "start_date": node.get("start_date") or "",
        "end_date": node.get("end_date") or "",
        "broadcast_day": broadcast.get("day_of_the_week") or "",
        "broadcast_time": broadcast.get("start_time") or "",
        "num_episodes": node.get("num_episodes"),
    }


def register_mal_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            name="mal.search_anime",
            description=(
                "Search official MyAnimeList for anime by a title query. "
                "Returns only real ids that may be selected as candidates."
            ),
            input_model=SearchMALInput,
            output_model=SearchMALOutput,
            handler=_search_mal,
            permission="mal:read",
            records_evidence=True,
            timeout_seconds=40,
        )
    )


mal_search_tool = _search_mal
