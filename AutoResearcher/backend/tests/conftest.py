"""Shared test fixtures for all backend tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.models.events import EventIDGenerator


class MockLLMClient:
    """Mock LLM client that returns predetermined responses."""

    def __init__(self, response: dict[str, Any] | str = ""):
        self._response = response
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.call_count += 1
        self.last_messages = messages
        if isinstance(self._response, dict):
            return json.dumps(self._response)
        return self._response

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        self.call_count += 1
        self.last_messages = messages
        text = self._response if isinstance(self._response, str) else json.dumps(self._response)
        for char in text:
            yield char

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_messages = messages
        if isinstance(self._response, dict):
            return self._response
        return json.loads(self._response)


class MockSearchClient:
    """Mock search client with controllable responses."""

    def __init__(
        self,
        results: list[dict[str, Any]] | None = None,
        error: Exception | None = None,
    ):
        self._results = results or [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
                "score": 0.95,
            }
        ]
        self._error = error
        self.call_count = 0
        self.queries: list[str] = []

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        self.call_count += 1
        self.queries.append(query)
        if self._error:
            raise self._error
        return self._results


class MockVectorStoreClient:
    """Mock vector store client for testing."""

    def __init__(self, query_results: list[dict[str, Any]] | None = None):
        self._query_results = query_results or []
        self.added: list[dict[str, Any]] = []

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        self.added.append({"documents": documents, "metadatas": metadatas, "ids": ids})

    async def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self._query_results

    async def delete(self, ids: list[str]) -> None:
        pass
