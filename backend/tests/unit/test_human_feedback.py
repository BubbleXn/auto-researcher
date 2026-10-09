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


def _build_two_pause_graph(checkpointer):
    """START → human_feedback →(searching)→ human_feedback →(else)→ END.

    Simulates the more_search round-trip: the node pauses twice in one
    session, which is where the resume flag used to swallow the second
    prompt events.
    """
    node = HumanFeedbackNode()
    graph = StateGraph(ResearchState)
    graph.add_node("human_feedback", node)
    graph.set_entry_point("human_feedback")
    graph.add_conditional_edges(
        "human_feedback",
        lambda s: (
            "human_feedback"
            if s.get("phase") == ResearchPhase.SEARCHING.value
            else END
        ),
        {"human_feedback": "human_feedback", END: END},
    )
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
    for rid in ["test-feedback-id", "test-interrupt-1", "test-resume-1",
                "test-outline-1", "test-route-search", "test-seed-tasks",
                "test-two-pause"]:
        transient_store.unregister(rid)


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
    transient_store.register(research_id, id_gen, asyncio.Queue(), is_resume=True)

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

    transient_store.register(research_id, id_gen, asyncio.Queue(), is_resume=True)

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


@pytest.mark.asyncio
async def test_human_feedback_routes_to_searcher_on_search_request() -> None:
    """Feedback containing '搜索' sets phase to SEARCHING for conditional routing."""
    saver = InMemorySaver()
    graph = _build_mini_graph(saver)

    research_id = "test-route-search"
    id_gen = EventIDGenerator()
    transient_store.register(research_id, id_gen, asyncio.Queue())

    state = _make_state(research_id)
    config = {"configurable": {"thread_id": research_id}}

    async for _ in graph.astream(state, config=config):
        pass

    transient_store.register(research_id, id_gen, asyncio.Queue(), is_resume=True)

    resume_data = {"feedback": "需要补充搜索"}
    collected = []
    async for event in graph.astream(Command(resume=resume_data), config=config):
        if "__interrupt__" in event:
            continue
        for _, output in event.items():
            collected.append(output)

    assert collected[0]["phase"] == ResearchPhase.SEARCHING.value


@pytest.mark.asyncio
async def test_more_search_seeds_pending_sub_tasks() -> None:
    """action=more_search seeds pending sub-tasks from the critique aspects."""
    saver = InMemorySaver()
    graph = _build_mini_graph(saver)

    research_id = "test-seed-tasks"
    id_gen = EventIDGenerator()
    transient_store.register(research_id, id_gen, asyncio.Queue())

    state = _make_state(research_id)
    state["sub_tasks"] = [
        {"id": "task_1", "query": "existing topic", "status": "completed", "result": "ok"},
    ]
    state["critique"] = {
        "missing_aspects": ["New Aspect A", "existing topic", 123, "New Aspect B"],
    }
    config = {"configurable": {"thread_id": research_id}}

    async for _ in graph.astream(state, config=config):
        pass

    transient_store.register(research_id, id_gen, asyncio.Queue(), is_resume=True)

    collected = []
    async for event in graph.astream(
        Command(resume={"feedback": "需要补充搜索", "action": "more_search"}),
        config=config,
    ):
        if "__interrupt__" in event:
            continue
        for _, output in event.items():
            collected.append(output)

    assert collected[0]["phase"] == ResearchPhase.SEARCHING.value
    pending = [t for t in collected[0]["sub_tasks"] if t["status"] == "pending"]
    # Non-string and duplicate queries are filtered out.
    assert [t["query"] for t in pending] == ["New Aspect A", "New Aspect B"]
    assert [t["id"] for t in pending] == ["extra_1", "extra_2"]


@pytest.mark.asyncio
async def test_second_pause_reemits_input_prompt() -> None:
    """After a resume replay, a later pause must emit the prompt events again.

    Regression: is_resume stayed True forever, so the second pause in a
    session never delivered human_input_needed and the client deadlocked.
    """
    saver = InMemorySaver()
    graph = _build_two_pause_graph(saver)

    research_id = "test-two-pause"
    config = {"configurable": {"thread_id": research_id}}
    id_gen = EventIDGenerator()

    # Round 1: the first pause emits the prompt.
    q1: asyncio.Queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, q1)
    async for _ in graph.astream(_make_state(research_id), config=config):
        pass
    assert q1.qsize() == 2  # phase_change + human_input_needed

    # Resume replay: research.py re-registers with is_resume=True; the replay
    # must stay silent, and more_search routes back into the node.
    q2: asyncio.Queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, q2, is_resume=True)
    async for _ in graph.astream(
        Command(resume={"feedback": "需要补充搜索", "action": "more_search"}),
        config=config,
    ):
        pass
    assert q2.qsize() == 2  # the second pause re-emits — the regression
    snapshot = await graph.aget_state(config)
    assert snapshot.next  # still paused waiting for round-2 feedback
    assert transient_store.get_is_resume(research_id) is False

    # The second resume replay is silent too (prompt already delivered).
    q3: asyncio.Queue = asyncio.Queue()
    transient_store.register(research_id, id_gen, q3, is_resume=True)
    async for _ in graph.astream(
        Command(resume={"feedback": "继续", "action": "proceed"}),
        config=config,
    ):
        pass
    assert q3.qsize() == 0
    snapshot = await graph.aget_state(config)
    assert not snapshot.next
