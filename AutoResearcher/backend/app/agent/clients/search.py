"""Tavily-based search client implementation."""

from __future__ import annotations

from typing import Any

from tavily import AsyncTavilyClient

from app.core.config import settings


class TavilySearchClient:
    """Production search client using Tavily API."""

    def __init__(self, api_key: str | None = None):
        self._client = AsyncTavilyClient(api_key=api_key or settings.tavily_api_key)

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        response = await self._client.search(
            query=query,
            max_results=max_results,
            include_raw_content=include_raw_content,
        )
        results: list[dict[str, Any]] = []
        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                }
            )
        return results
