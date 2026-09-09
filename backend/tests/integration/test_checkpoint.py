"""Tests for checkpoint persistence with AsyncSqliteSaver."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from app.agent.graph import build_research_graph
from app.agent.state import create_initial_state
from app.api.research import (
    _active_research,
    _compiled_graphs,
    _feedback_futures,
    _run_research_stream,
)
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
    for rid in [
        "ckpt-test-1",
        "ckpt-test-2",
        "ckpt-test-3",
        "reconnect-missing",
        "reconnect-resume",
        "reconnect-completed",
    ]:
        transient_store.unregister(rid)
        _active_research.pop(rid, None)
        _compiled_graphs.pop(rid, None)
        _feedback_futures.pop(rid, None)


@pytest.fixture
async def checkpointer():
    async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        yield saver


@pytest.mark.asyncio
async def test_checkpoint_excludes_transient_fields(checkpointer) -> None:
    """Non-serializable transient objects must not appear in checkpoint."""
    saver = checkpointer

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
async def test_checkpoint_preserves_last_event_id(checkpointer) -> None:
    """_last_event_id persists across interrupt/resume."""
    saver = checkpointer

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
    transient_store.register(research_id, id_gen, asyncio.Queue(), is_resume=True)
    async for _ in graph.astream(Command(resume={"feedback": "ok"}), config=config):
        pass

    snapshot2 = await graph.aget_state(config)
    last_eid2 = snapshot2.values.get("_last_event_id", 0)
    assert last_eid2 > last_eid, "_last_event_id should increase after resume"


@pytest.mark.asyncio
async def test_checkpoint_state_restores_correctly(checkpointer) -> None:
    """State values persist correctly through checkpoint across interrupt."""
    saver = checkpointer

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


@pytest.mark.asyncio
async def test_reconnection_missing_checkpoint_sends_error_and_cleans_up(checkpointer) -> None:
    """Reconnecting to a missing checkpoint yields an error and cleans resources."""
    saver = checkpointer
    research_id = "reconnect-missing"
    semaphore = asyncio.Semaphore(3)

    events: list[str] = []
    async for sse_str in _run_research_stream(
        research_id=research_id,
        query="missing checkpoint test",
        llm=_MockLLM(),
        search=_MockSearch(),
        vectorstore=_MockVS(),
        semaphore=semaphore,
        checkpointer=saver,
        resume_from_event_id=1,
    ):
        events.append(sse_str)

    assert any("event: error" in e for e in events)
    assert research_id not in _active_research
    assert research_id not in _compiled_graphs


@pytest.mark.asyncio
async def test_reconnection_resumes_interrupted_session_and_cleans_up(checkpointer) -> None:
    """Reconnect to an interrupted session, provide feedback, and verify cleanup."""
    saver = checkpointer
    research_id = "reconnect-resume"
    semaphore = asyncio.Semaphore(3)

    # Run graph directly until it interrupts at human_feedback
    graph = build_research_graph(
        llm=_MockLLM(), search=_MockSearch(), vectorstore=_MockVS(), checkpointer=saver
    )
    state = create_initial_state(research_id, "reconnection resume test")
    config = {"configurable": {"thread_id": research_id}}
    async for _ in graph.astream(state, config=config):
        pass

    snapshot = await graph.aget_state(config)
    assert snapshot.next, "Graph should be interrupted before reconnection"

    # Schedule feedback so the reconnected stream can resume
    async def _provide_feedback() -> None:
        await asyncio.sleep(0.05)
        future = _feedback_futures[research_id]
        future.set_result({"feedback": "ok"})

    feedback_task = asyncio.create_task(_provide_feedback())

    events: list[str] = []
    async for sse_str in _run_research_stream(
        research_id=research_id,
        query="reconnection resume test",
        llm=_MockLLM(),
        search=_MockSearch(),
        vectorstore=_MockVS(),
        semaphore=semaphore,
        checkpointer=saver,
        resume_from_event_id=1,
    ):
        events.append(sse_str)

    await feedback_task

    # Should have emitted resume_state, phase changes, and done
    assert any("event: resume_state" in e for e in events)
    assert any("event: done" in e for e in events)
    assert research_id not in _active_research
    assert research_id not in _compiled_graphs
    assert transient_store.get_event_queue(research_id) is None


@pytest.mark.asyncio
async def test_reconnection_completed_session_sends_resume_state_and_cleans_up(checkpointer) -> None:
    """Reconnecting to a completed session sends resume_state and cleans up without feedback."""
    saver = checkpointer
    research_id = "reconnect-completed"
    semaphore = asyncio.Semaphore(3)

    # First run a full session through _run_research_stream
    async def _provide_feedback() -> None:
        await asyncio.sleep(0.05)
        future = _feedback_futures[research_id]
        future.set_result({"feedback": "ok"})

    feedback_task = asyncio.create_task(_provide_feedback())

    async for _ in _run_research_stream(
        research_id=research_id,
        query="completed session test",
        llm=_MockLLM(),
        search=_MockSearch(),
        vectorstore=_MockVS(),
        semaphore=semaphore,
        checkpointer=saver,
    ):
        pass

    await feedback_task
    assert research_id not in _active_research

    # Now reconnect
    events: list[str] = []
    async for sse_str in _run_research_stream(
        research_id=research_id,
        query="completed session test",
        llm=_MockLLM(),
        search=_MockSearch(),
        vectorstore=_MockVS(),
        semaphore=semaphore,
        checkpointer=saver,
        resume_from_event_id=1,
    ):
        events.append(sse_str)

    assert any("event: resume_state" in e for e in events)
    assert not any("event: done" in e for e in events)
    assert research_id not in _active_research
    assert research_id not in _compiled_graphs
