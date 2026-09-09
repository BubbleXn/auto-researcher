"""Unit tests for TavilySearchClient retry behavior."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.clients.search import TavilySearchClient


@pytest.fixture
def no_retry_delay():
    with patch.object(asyncio, "sleep", new=AsyncMock()):
        yield


@pytest.fixture
def mock_tavily():
    with patch("app.agent.clients.search.AsyncTavilyClient") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_search_retries_on_transient_failure(mock_tavily, no_retry_delay):
    mock_tavily.search = AsyncMock(side_effect=[ConnectionError("boom"), {"results": []}])

    client = TavilySearchClient(api_key="test-key")
    result = await client.search("query")

    assert result == []
    assert mock_tavily.search.await_count == 2


@pytest.mark.asyncio
async def test_search_raises_after_max_retries(mock_tavily, no_retry_delay):
    mock_tavily.search = AsyncMock(side_effect=ConnectionError("boom"))

    client = TavilySearchClient(api_key="test-key")
    with pytest.raises(ConnectionError):
        await client.search("query")

    assert mock_tavily.search.await_count == 3


@pytest.mark.asyncio
async def test_search_returns_parsed_results(mock_tavily, no_retry_delay):
    mock_tavily.search = AsyncMock(
        return_value={
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "content",
                    "score": 0.95,
                }
            ]
        }
    )

    client = TavilySearchClient(api_key="test-key")
    result = await client.search("query")

    assert len(result) == 1
    assert result[0]["title"] == "Test"
    assert result[0]["score"] == 0.95
