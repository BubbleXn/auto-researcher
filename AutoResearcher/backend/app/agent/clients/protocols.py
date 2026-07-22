"""
Dependency protocols for LLM, Search, and VectorStore clients.
All agent nodes receive these via constructor injection, enabling mock-based testing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM interactions. Mock this in unit tests."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send messages to LLM and return the text response."""
        ...

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream LLM response token by token."""
        ...

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate a response conforming to a JSON schema."""
        ...


@runtime_checkable
class SearchClient(Protocol):
    """Protocol for web search. Mock this to avoid real network calls in tests."""

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search the web and return results.

        Each result dict contains:
          - title: str
          - url: str
          - content: str (snippet or full content)
          - score: float (relevance score, 0-1)
        """
        ...


@runtime_checkable
class VectorStoreClient(Protocol):
    """Protocol for vector storage. Abstracts ChromaDB, Milvus, Qdrant, etc."""

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        """Store documents with metadata."""
        ...

    async def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query similar documents.

        Each result dict contains:
          - id: str
          - document: str
          - metadata: dict
          - distance: float
        """
        ...

    async def delete(self, ids: list[str]) -> None:
        """Delete documents by IDs."""
        ...
