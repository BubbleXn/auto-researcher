"""Tavily-based search client implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from tavily import AsyncTavilyClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_RETRIES = 3


class TavilySearchClient:
    """Production search client using Tavily API."""

    def __init__(self, api_key: str | None = None):
        self._client = AsyncTavilyClient(api_key=api_key or settings.tavily_api_key)

    @retry(
        stop=stop_after_attempt(_DEFAULT_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        response = await asyncio.wait_for(
            self._client.search(
                query=query,
                max_results=max_results,
                include_raw_content=include_raw_content,
            ),
            timeout=_DEFAULT_TIMEOUT_SECONDS,
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
