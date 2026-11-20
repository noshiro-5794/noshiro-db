"""Typed public-knowledge and MAL search tools for native retrieval agents."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.contexts.identity import resolution
from api.contexts.presentation.catalogue import entity_page
from api.contexts.presentation.detail import entity_detail
from api.contexts.presentation.fragments import fetch
from api.worker.providers.mal import MALClient
from api.worker.session import session_scope


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchEntitiesInput(ToolInput):
    query: str = Field(default="", max_length=256)
    collection: str = Field(default="", max_length=64)
    language: str = Field(default="", max_length=35)
    limit: int = Field(default=20, ge=1, le=50)


class GetEntityInput(ToolInput):
    entity_id: UUID
    language: str = Field(default="", max_length=35)


class SearchMALInput(ToolInput):
    query: str = Field(min_length=1, max_length=160)
    limit: int = Field(default=10, ge=1, le=20)


class Results(BaseModel):
    results: list[dict[str, Any]]


class EntityResult(BaseModel):
    entity: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolDefinition[Input: BaseModel, Output: BaseModel]:
    name: str
    description: str
    input_model: type[Input]
    output_model: type[Output]
    handler: Callable[[Input], Awaitable[Output]]
    permission: str = "knowledge:read"
    timeout_seconds: float = 30

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }

    async def execute(self, parameters: dict[str, Any]) -> Output:
        value = self.input_model.model_validate(parameters)
        async with asyncio.timeout(self.timeout_seconds):
            result = await self.handler(value)
        return self.output_model.model_validate(result)


async def search_entities(value: SearchEntitiesInput) -> Results:
    async with session_scope() as session:
        _, results = await entity_page(
            session,
            keyword=value.query.strip(),
            scope="all",
            collection=value.collection.strip(),
            subject_type="",
            safe_only=False,
            ordering="",
            language=value.language,
            page=1,
            page_size=value.limit,
            cluster_scope=True,
            count_total=False,
        )
    return Results(results=results)


async def get_entity(value: GetEntityInput) -> EntityResult:
    async with session_scope() as session:
        root = await resolution.resolve(session, value.entity_id)
        if root is None or not await resolution.is_active(session, root):
            raise LookupError("Public entity not found.")
        members = await resolution.cluster_ids(session, root)
        if not await resolution.is_public(session, members):
            raise LookupError("Public entity not found.")
        result = await entity_detail(
            session,
            root=root,
            cluster_ids=[str(member) for member in members],
            language=value.language,
        )
    return EntityResult(entity=result)


def compact_mal_node(node: Any) -> dict[str, Any] | None:
    if not isinstance(node, dict) or not isinstance(node.get("id"), int):
        return None
    alternatives = node.get("alternative_titles")
    alternatives = alternatives if isinstance(alternatives, dict) else {}
    broadcast = node.get("broadcast")
    broadcast = broadcast if isinstance(broadcast, dict) else {}
    return {
        "id": node["id"],
        "title": node.get("title") or "",
        "alternative_titles": {
            "synonyms": alternatives.get("synonyms") or [],
            "en": alternatives.get("en") or "",
            "ja": alternatives.get("ja") or "",
        },
        "media_type": node.get("media_type") or "",
        "status": node.get("status") or "",
        "start_date": node.get("start_date") or "",
        "end_date": node.get("end_date") or "",
        "broadcast_day": broadcast.get("day_of_the_week") or "",
        "broadcast_time": broadcast.get("start_time") or "",
        "num_episodes": node.get("num_episodes"),
    }


async def search_mal(value: SearchMALInput) -> Results:
    async with session_scope() as session:
        rows = await fetch(session, "SELECT storage_policy FROM provider WHERE slug='mal'", {})
    client = MALClient()
    client.forbid_storage(forbidden=bool(rows and rows[0].storage_policy == "forbidden"))
    try:
        payload = await asyncio.to_thread(
            client.search_anime, query=value.query.strip(), limit=value.limit
        )
    finally:
        client.close()
    results = []
    for wrapper in payload.get("data") or []:
        if not isinstance(wrapper, dict):
            continue
        node = wrapper.get("node") if isinstance(wrapper.get("node"), dict) else wrapper
        compact = compact_mal_node(node)
        if compact is not None:
            results.append(compact)
    return Results(results=results)


DEFINITIONS: tuple[ToolDefinition[Any, Any], ...] = (
    ToolDefinition(
        "knowledge.search_entities",
        "Search safe, public knowledge-base entity projections.",
        SearchEntitiesInput,
        Results,
        search_entities,
    ),
    ToolDefinition(
        "knowledge.get_entity",
        "Get one safe, public entity projection.",
        GetEntityInput,
        EntityResult,
        get_entity,
    ),
    ToolDefinition(
        "mal.search_anime",
        "Search official MyAnimeList for anime by a title query. "
        "Returns only real ids that may be selected as candidates.",
        SearchMALInput,
        Results,
        search_mal,
        permission="mal:read",
        timeout_seconds=40,
    ),
)

TOOLS = {tool.name: tool for tool in DEFINITIONS}
