"""Unit tests for the HumanFeedbackNode."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agent.nodes.human_feedback import HumanFeedbackNode
from app.agent.state import ResearchPhase
from app.core import session_registry
from app.models.events import EventIDGenerator


def _make_state() -> dict[str, Any]:
    event_queue: asyncio.Queue = asyncio.Queue()
    return {
        "research_id": "test-feedback-id",
        "query": "test query",
        "phase": "critiquing",
        "plan": {"outline": ["Section 1", "Section 2", "Section 3"]},
        "sub_tasks": [],
        "search_results": [],
        "retry_count": 0,
        "max_retries": 3,
        "human_input_requested": False,
        "human_feedback": None,
        "_id_gen": EventIDGenerator(),
        "_event_queue": event_queue,
    }


@pytest.fixture(autouse=True)
def cleanup_sessions():
    yield
    session_registry.remove_session("test-feedback-id")


@pytest.mark.asyncio
async def test_human_feedback_emits_events_and_waits() -> None:
    node = HumanFeedbackNode()
    state = _make_state()
    event_queue = state["_event_queue"]

    async def _provide_feedback():
        # Wait a bit for the node to start waiting
        await asyncio.sleep(0.1)
        # Check that events were pushed to queue
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())
        assert len(events) == 2  # phase_change + human_input_needed
        assert events[0].event.value == "phase_change"
        assert events[1].event.value == "human_input_needed"
        # Set feedback via session_registry
        session = session_registry.get_session("test-feedback-id")
        session["human_feedback"] = "看起来不错，继续吧"
        event: asyncio.Event = session["_feedback_event"]
        event.set()

    feedback_task = asyncio.create_task(_provide_feedback())
    result = await node(state)
    await feedback_task

    assert result["phase"] == ResearchPhase.WRITING.value
    assert result["human_feedback"] == "看起来不错，继续吧"


@pytest.mark.asyncio
async def test_human_feedback_applies_modified_outline() -> None:
    node = HumanFeedbackNode()
    state = _make_state()

    async def _provide_modified_outline():
        await asyncio.sleep(0.1)
        session = session_registry.get_session("test-feedback-id")
        session["human_feedback"] = "修改了大纲"
        session["modified_outline"] = [
            {"section": "New Section 1"},
            {"section": "New Section 2"},
        ]
        session["_feedback_event"].set()

    task = asyncio.create_task(_provide_modified_outline())
    result = await node(state)
    await task

    assert result["plan"]["outline"] == ["New Section 1", "New Section 2"]


@pytest.mark.asyncio
async def test_human_feedback_transitions_to_writing() -> None:
    node = HumanFeedbackNode()
    state = _make_state()

    async def _quick_feedback():
        await asyncio.sleep(0.05)
        session = session_registry.get_session("test-feedback-id")
        session["human_feedback"] = "ok"
        session["_feedback_event"].set()

    task = asyncio.create_task(_quick_feedback())
    result = await node(state)
    await task

    assert result["phase"] == ResearchPhase.WRITING.value
    assert result["human_input_requested"] is False
