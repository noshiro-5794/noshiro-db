"""Configured Tavily search for bounded external evidence retrieval."""

from __future__ import annotations

import os
from typing import Any

import httpx

from api.shared.outbound import proxy_for


def configured() -> bool:
    return os.environ.get("WEB_SEARCH_PROVIDER") == "tavily" and bool(
        os.environ.get("WEB_SEARCH_API_KEY")
    )


async def search(query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
    if not configured():
        return []
    base = os.environ.get("WEB_SEARCH_BASE_URL", "https://api.tavily.com").rstrip("/")
    async with httpx.AsyncClient(
        timeout=float(os.environ.get("WEB_SEARCH_TIMEOUT", "20")), proxy=proxy_for(base)
    ) as client:
        response = await client.post(
            f"{base}/search",
            json={
                "api_key": os.environ["WEB_SEARCH_API_KEY"],
                "query": query,
                "max_results": max(1, min(max_results, 10)),
                "include_answer": False,
                "include_raw_content": False,
            },
        )
        response.raise_for_status()
    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "url": item["url"],
            "content": item.get("content", ""),
            "score": item.get("score"),
        }
        for item in data.get("results") or []
        if isinstance(item, dict) and item.get("url")
    ]
