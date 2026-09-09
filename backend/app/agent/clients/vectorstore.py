"""ChromaDB-based vector store client implementation."""

from __future__ import annotations

import asyncio
from typing import Any

import chromadb


class ChromaVectorStoreClient:
    """Production vector store client using ChromaDB."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "research_documents",
    ):
        self._chroma = chromadb.HttpClient(host=host, port=port)
        self._collection_name = collection_name
        self._collection: chromadb.Collection | None = None

    async def _get_collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = await asyncio.to_thread(
                self._chroma.get_or_create_collection,
                name=self._collection_name,
            )
        return self._collection

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        collection = await self._get_collection()
        await asyncio.to_thread(
            collection.add,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    async def query(
        self,
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        collection = await self._get_collection()
        kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        raw = await asyncio.to_thread(collection.query, **kwargs)
        results: list[dict[str, Any]] = []
        for i in range(len(raw["ids"][0])):
            results.append(
                {
                    "id": raw["ids"][0][i],
                    "document": raw["documents"][0][i] if raw["documents"] else "",
                    "metadata": raw["metadatas"][0][i] if raw["metadatas"] else {},
                    "distance": raw["distances"][0][i] if raw["distances"] else 0.0,
                }
            )
        return results

    async def delete(self, ids: list[str]) -> None:
        collection = await self._get_collection()
        await asyncio.to_thread(collection.delete, ids=ids)
