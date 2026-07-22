"""Unit tests for the HumanFeedbackNode with interrupt()-based flow."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.agent.nodes.human_feedback import HumanFeedbackNode
from app.agent.state import ResearchPhase, ResearchState
from app.core import transient_store
from app.models.events import EventIDGenerator, SSEEvent


def _build_mini_graph(checkpointer):
    """A minimal graph: START → human_feedback → END."""
    node = HumanFeedbackNode()
    graph = StateGraph(ResearchState)
    graph.add_node("human_feedback", node)
    graph.set_entry_point("human_feedback")
    graph.add_edge("human_feedback", END)
    return graph.compile(checkpointer=checkpointer)


def _make_state(research_id: str = "test-feedback-id") -> dict[str, Any]:
    return {
        "research_id": research_id,
        "query": "test query",
        "phase": "critiquing",
        "plan": {"outline": ["Section 1", "Section 2", "Section 3"]},
        "sub_tasks": [],
        "search_results": [],
        "retry_count": 0,
        "max_retries": 3,
        "human_input_requested": False,
        "human_feedback": None,
        "_last_event_id": 0,
    }


@pytest.fixture(autouse=True)
def cleanup():
    yield
    transient_store.unregister("test-feedback-id")
    transient_store.unregister("test-interrupt-1")
    transient_store.unregister("test-resume-1")
    transient_store.unregister("test-outline-1")


@pytest.mark.asyncio
async def test_human_feedback_interrupts_and_emits_events() -> None:
    """interrupt() halts graph and events are pushed to queue before halt."""
    saver = InMemorySaver()
    graph = _build_mini_graph(saver)

    research_id = "test-interrupt-1"
    event_queue: asyncio.Queue = asyncio.Queue()
    id_gen = EventIDGenerator()
    transient_store.register(research_id, id_gen, event_queue)

    state = _make_state(research_id)
    config = {"configurable": {"thread_id": research_id}}

    async for event in graph.astream(state, config=config):
        pass

    # Events should have been pushed to the queue
    queue_events: list[SSEEvent] = []
    while not event_queue.empty():
        queue_events.append(await event_queue.get())
    assert len(queue_events) == 2
    assert queue_events[0].event.value == "phase_change"
    assert queue_events[1].event.value == "human_input_needed"

    # Graph should be interrupted
    snapshot = await graph.aget_state(config)
    assert snapshot.next


@pytest.mark.asyncio
async def test_human_feedback_resume_returns_feedback() -> None:
    """Resume with Command(resume=data) returns feedback and transitions to writing."""
    saver = InMemorySaver()
    graph = _build_mini_graph(saver)

    research_id = "test-resume-1"
    event_queue: asyncio.Queue = asyncio.Queue()
    id_gen = EventIDGenerator()
    transient_store.register(research_id, id_gen, event_queue)

    state = _make_state(research_id)
    config = {"configurable": {"thread_id": research_id}}

    # Phase 1: run until interrupt
    async for _ in graph.astream(state, config=config):
        pass

    # Phase 2: resume with feedback (re-register transients for re-execution)
    transient_store.register(research_id, id_gen, asyncio.Queue())

    resume_data = {"feedback": "看起来不错，继续吧"}
    collected: list[dict] = []
    async for event in graph.astream(Command(resume=resume_data), config=config):
        if "__interrupt__" in event:
            continue
        for _, output in event.items():
            collected.append(output)

    assert len(collected) == 1
    result = collected[0]
    assert result["phase"] == ResearchPhase.WRITING.value
    assert result["human_feedback"] == "看起来不错，继续吧"
    assert result["human_input_requested"] is False


@pytest.mark.asyncio
async def test_human_feedback_applies_modified_outline() -> None:
    """Modified outline in resume data updates the plan."""
    saver = InMemorySaver()
    graph = _build_mini_graph(saver)

    research_id = "test-outline-1"
    event_queue: asyncio.Queue = asyncio.Queue()
    id_gen = EventIDGenerator()
    transient_store.register(research_id, id_gen, event_queue)

    state = _make_state(research_id)
    config = {"configurable": {"thread_id": research_id}}

    async for _ in graph.astream(state, config=config):
        pass

    transient_store.register(research_id, id_gen, asyncio.Queue())

    resume_data = {
        "feedback": "修改了大纲",
        "modified_outline": [
            {"section": "New Section 1"},
            {"section": "New Section 2"},
        ],
    }

    collected = []
    async for event in graph.astream(Command(resume=resume_data), config=config):
        if "__interrupt__" in event:
            continue
        for _, output in event.items():
            collected.append(output)

    assert collected[0]["plan"]["outline"] == ["New Section 1", "New Section 2"]
