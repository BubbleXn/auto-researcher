"""Unit tests for the Writer node."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.agent.nodes.writer import WriterNode
from app.agent.state import ResearchPhase
from app.core import transient_store
from app.models.events import EventIDGenerator


class MockStreamLLMClient:
    """Mock LLM that yields tokens from a predetermined response."""

    def __init__(self, response_text: str = "# Test Report\n\nThis is a test report."):
        self._response_text = response_text
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    async def generate(self, messages, *, temperature=0.7, max_tokens=4096, response_format=None) -> str:
        self.call_count += 1
        self.last_messages = messages
        return self._response_text

    async def generate_stream(self, messages, *, temperature=0.7, max_tokens=4096) -> AsyncIterator[str]:
        self.call_count += 1
        self.last_messages = messages
        for char in self._response_text:
            yield char

    async def generate_structured(self, messages, *, schema, temperature=0.0) -> dict:
        self.call_count += 1
        return {}


class MockVectorStoreClient:
    def __init__(self, query_results=None):
        self._query_results = query_results or []
        self.added: list[dict] = []

    async def add_documents(self, documents, metadatas, ids):
        self.added.append({"documents": documents, "metadatas": metadatas, "ids": ids})

    async def query(self, query_text, *, n_results=5, where=None):
        return self._query_results

    async def delete(self, ids):
        pass


def _make_writer_state() -> dict[str, Any]:
    transient_store.register("test-id", EventIDGenerator(), asyncio.Queue())
    return {
        "research_id": "test-id",
        "query": "test research question",
        "phase": "critiquing",
        "plan": {"outline": ["Introduction", "Analysis", "Conclusion"]},
        "search_results": [
            {"title": "Source 1", "url": "https://example.com/1", "content": "Content about topic 1", "score": 0.9, "sub_task_id": "task_1"},
            {"title": "Source 2", "url": "https://example.com/2", "content": "Content about topic 2", "score": 0.8, "sub_task_id": "task_2"},
        ],
    }


@pytest.fixture(autouse=True)
def cleanup():
    yield
    transient_store.unregister("test-id")


@pytest.mark.asyncio
async def test_writer_generates_report() -> None:
    llm = MockStreamLLMClient("# Report\n\nTest content.")
    writer = WriterNode(llm=llm)
    state = _make_writer_state()

    result = await writer(state)

    assert result["phase"] == ResearchPhase.COMPLETED.value
    assert result["report"] == "# Report\n\nTest content."
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_writer_extracts_sources() -> None:
    llm = MockStreamLLMClient("report")
    writer = WriterNode(llm=llm)
    state = _make_writer_state()

    result = await writer(state)

    assert len(result["sources"]) == 2
    assert result["sources"][0]["url"] == "https://example.com/1"
    assert result["sources"][1]["url"] == "https://example.com/2"


@pytest.mark.asyncio
async def test_writer_deduplicates_sources() -> None:
    llm = MockStreamLLMClient("report")
    writer = WriterNode(llm=llm)
    state = _make_writer_state()
    # Add duplicate URL
    state["search_results"].append({
        "title": "Source 1 duplicate", "url": "https://example.com/1",
        "content": "Same URL", "score": 0.7, "sub_task_id": "task_1"
    })

    result = await writer(state)

    assert len(result["sources"]) == 2  # deduplicated by URL


@pytest.mark.asyncio
async def test_writer_emits_phase_change_and_step() -> None:
    llm = MockStreamLLMClient("report")
    writer = WriterNode(llm=llm)
    state = _make_writer_state()

    result = await writer(state)

    sse_events = result["_sse_events"]
    phase_events = [e for e in sse_events if e["event"] == "phase_change"]
    step_events = [e for e in sse_events if e["event"] == "agent_step"]

    assert len(phase_events) >= 1
    assert phase_events[0]["data"]["phase"] == "writing"
    assert phase_events[0]["data"]["from_phase"] == "awaiting_human_input"

    assert len(step_events) >= 1
    assert step_events[0]["data"]["action"] == "writing_report"


@pytest.mark.asyncio
async def test_writer_pushes_chunks_to_queue() -> None:
    long_text = "A" * 500  # will create multiple chunks (CHUNK_FLUSH_SIZE=150)
    llm = MockStreamLLMClient(long_text)
    writer = WriterNode(llm=llm)
    state = _make_writer_state()
    event_queue = transient_store.get_event_queue("test-id")

    result = await writer(state)

    # Collect all chunks from the queue
    chunks = []
    while not event_queue.empty():
        ev = await event_queue.get()
        if ev.event.value == "report_chunk":
            chunks.append(ev)

    assert len(chunks) >= 2  # at least 2 chunks for 500 chars
    # Last chunk should have is_final=True
    assert chunks[-1].data["is_final"] is True


@pytest.mark.asyncio
async def test_writer_queries_vectorstore_for_context() -> None:
    llm = MockStreamLLMClient("report")
    vs = MockVectorStoreClient(query_results=[
        {"id": "pdf_1", "document": "PDF content about topic", "metadata": {"source_filename": "paper.pdf"}, "distance": 0.1}
    ])
    writer = WriterNode(llm=llm, vectorstore=vs)
    state = _make_writer_state()

    await writer(state)

    # The LLM should have received the extra context
    user_msg = llm.last_messages[-1]["content"]
    assert "Additional reference materials" in user_msg
    assert "paper.pdf" in user_msg


@pytest.mark.asyncio
async def test_writer_works_without_vectorstore() -> None:
    llm = MockStreamLLMClient("report")
    writer = WriterNode(llm=llm, vectorstore=None)
    state = _make_writer_state()

    result = await writer(state)

    assert result["report"] == "report"
    assert result["phase"] == ResearchPhase.COMPLETED.value
