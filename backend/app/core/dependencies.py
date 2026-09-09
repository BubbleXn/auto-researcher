"""Dependency injection for FastAPI. Provides client instances to route handlers."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
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
    if settings.use_mock:
        from app.agent.clients.mock import MockLLMClient
        logger.info("Using MockLLMClient (USE_MOCK=true)")
        return MockLLMClient()
    from app.agent.clients.llm import OpenAILLMClient
    return OpenAILLMClient()


@lru_cache
def get_search_client() -> SearchClient:
    if settings.use_mock:
        from app.agent.clients.mock import MockSearchClient
        logger.info("Using MockSearchClient (USE_MOCK=true)")
        return MockSearchClient()
    from app.agent.clients.search import TavilySearchClient
    return TavilySearchClient()


@lru_cache
def get_vectorstore_client() -> VectorStoreClient:
    if settings.use_mock:
        logger.info("Using NoOpVectorStoreClient (USE_MOCK=true)")
        return _NoOpVectorStoreClient()  # type: ignore[return-value]
    try:
        from app.agent.clients.vectorstore import ChromaVectorStoreClient
        return ChromaVectorStoreClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
        )
    except Exception:
        logger.warning("ChromaDB unavailable, using no-op vector store")
        return _NoOpVectorStoreClient()  # type: ignore[return-value]
