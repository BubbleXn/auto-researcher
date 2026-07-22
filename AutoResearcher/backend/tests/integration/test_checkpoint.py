"""Tests for checkpoint persistence with InMemorySaver."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agent.graph import build_research_graph
from app.agent.state import create_initial_state
from app.core import transient_store
from app.models.events import EventIDGenerator


class _MockLLM:
    async def generate(self, messages, *, temperature=0.7, max_tokens=4096, response_format=None) -> str:
        return json.dumps(self._pick(messages))

    async def generate_stream(self, messages, *, temperature=0.7, max_tokens=4096) -> AsyncIterator[str]:
        for c in "# Report":
            yield c

    async def generate_structured(self, messages, *, schema, temperature=0.0) -> dict[str, Any]:
        return self._pick(messages)

    def _pick(self, messages):
        system = messages[0].get("content", "") if messages else ""
        if "planning" in system.lower() or "decompose" in system.lower():
            return {
                "outline": ["Section A", "Section B"],
                "sub_tasks": [{"id": "t1", "query": "topic A"}],
            }
        elif "critic" in system.lower() or "quality" in system.lower():
            return {
                "has_conflicts": False,
                "conflicts": [],
                "missing_aspects": [],
                "confidence_score": 0.95,
                "recommendation": "proceed",
            }
        return {}


class _MockSearch:
    async def search(self, query, *, max_results=5, include_raw_content=False):
        return [{"title": "R", "url": "https://x.com/r", "content": "content", "score": 0.9}]


class _MockVS:
    async def add_documents(self, documents, metadatas, ids):
        pass

    async def query(self, query_text, *, n_results=5, where=None):
        return []

    async def delete(self, ids):
        pass


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for rid in ["ckpt-test-1", "ckpt-test-2", "ckpt-test-3"]:
        transient_store.unregister(rid)


@pytest.mark.asyncio
async def test_checkpoint_excludes_transient_fields() -> None:
    """Non-serializable transient objects must not appear in checkpoint."""
    saver = InMemorySaver()

    research_id = "ckpt-test-1"
    id_gen = EventIDGenerator()
    event_queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, event_queue)

    graph = build_research_graph(
        llm=_MockLLM(), search=_MockSearch(), vectorstore=_MockVS(), checkpointer=saver
    )

    state = create_initial_state(research_id, "checkpoint test")
    config = {"configurable": {"thread_id": research_id}}

    async for _ in graph.astream(state, config=config):
        pass

    snapshot = await graph.aget_state(config)
    values = snapshot.values

    assert "_id_gen" not in values
    assert "_event_queue" not in values


@pytest.mark.asyncio
async def test_checkpoint_preserves_last_event_id() -> None:
    """_last_event_id persists across interrupt/resume."""
    saver = InMemorySaver()

    research_id = "ckpt-test-2"
    id_gen = EventIDGenerator()
    event_queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, event_queue)

    graph = build_research_graph(
        llm=_MockLLM(), search=_MockSearch(), vectorstore=_MockVS(), checkpointer=saver
    )

    state = create_initial_state(research_id, "event id test")
    config = {"configurable": {"thread_id": research_id}}

    # Run until interrupt
    async for _ in graph.astream(state, config=config):
        pass

    snapshot = await graph.aget_state(config)
    assert snapshot.next, "Should be interrupted"
    last_eid = snapshot.values.get("_last_event_id", 0)
    assert last_eid > 0, "_last_event_id should be positive after planner/searcher/critic"

    # Resume
    transient_store.register(research_id, id_gen, asyncio.Queue())
    async for _ in graph.astream(Command(resume={"feedback": "ok"}), config=config):
        pass

    snapshot2 = await graph.aget_state(config)
    last_eid2 = snapshot2.values.get("_last_event_id", 0)
    assert last_eid2 > last_eid, "_last_event_id should increase after resume"


@pytest.mark.asyncio
async def test_checkpoint_state_restores_correctly() -> None:
    """State values persist correctly through checkpoint across interrupt."""
    saver = InMemorySaver()

    research_id = "ckpt-test-3"
    id_gen = EventIDGenerator()
    event_queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, event_queue)

    graph = build_research_graph(
        llm=_MockLLM(), search=_MockSearch(), vectorstore=_MockVS(), checkpointer=saver
    )

    state = create_initial_state(research_id, "state restore test")
    config = {"configurable": {"thread_id": research_id}}

    async for _ in graph.astream(state, config=config):
        pass

    # Check state at interrupt point (before resume)
    snapshot = await graph.aget_state(config)
    vals = snapshot.values

    assert vals["research_id"] == "ckpt-test-3"
    assert vals["query"] == "state restore test"
    assert len(vals.get("plan", {}).get("outline", [])) > 0
    assert len(vals.get("sub_tasks", [])) > 0
    assert len(vals.get("search_results", [])) > 0
    assert vals.get("critique") is not None
    # Phase was set to "writing" by critic (recommendation=proceed),
    # but human_feedback node updates it further. At interrupt, the
    # human_feedback node hasn't returned yet, so check the snapshot
    # reflects pre-interrupt critic phase or the interrupt state.
    assert snapshot.next, "Should still be interrupted"
