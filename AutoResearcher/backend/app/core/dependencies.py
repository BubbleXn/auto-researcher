"""Dependency injection for FastAPI. Provides client instances to route handlers."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from app.agent.clients.llm import OpenAILLMClient
from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
from app.agent.clients.search import TavilySearchClient
from app.core.config import settings

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None


class _NoOpVectorStoreClient:
    async def add_documents(self, documents: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> None:
        pass

    async def query(self, query_text: str, *, n_results: int = 5, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return []

    async def delete(self, ids: list[str]) -> None:
        pass


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.max_concurrent_research)
    return _semaphore


@lru_cache
def get_llm_client() -> LLMClient:
    return OpenAILLMClient()


@lru_cache
def get_search_client() -> SearchClient:
    return TavilySearchClient()


@lru_cache
def get_vectorstore_client() -> VectorStoreClient:
    try:
        from app.agent.clients.vectorstore import ChromaVectorStoreClient
        return ChromaVectorStoreClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )
    except Exception:
        logger.warning("ChromaDB unavailable, using no-op vector store")
        return _NoOpVectorStoreClient()  # type: ignore[return-value]
