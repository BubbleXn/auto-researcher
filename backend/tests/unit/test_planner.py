"""
Unit tests for the Planner node.
Demonstrates how to mock LLMClient and test state transitions independently.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agent.nodes.planner import PlannerNode
from app.agent.state import ResearchPhase, create_initial_state
from app.core import transient_store
from app.models.events import EventIDGenerator


class MockLLMClient:
    """Mock LLM client that returns predetermined responses."""

    def __init__(self, response: dict[str, Any]):
        self._response = response
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.call_count += 1
        self.last_messages = messages
        import json

        return json.dumps(self._response)

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.last_messages = messages
        return self._response


@pytest.fixture
def mock_planner_response() -> dict[str, Any]:
    return {
        "outline": [
            "锂电池技术现状",
            "固态电池发展进展",
            "主要厂商技术路线对比",
        ],
        "sub_tasks": [
            {"id": "task_1", "query": "2024年锂电池技术现状和最新进展"},
            {"id": "task_2", "query": "固态电池技术发展进展2024"},
            {"id": "task_3", "query": "宁德时代比亚迪电池技术路线对比"},
        ],
    }


def _make_state(query: str = "test query") -> dict[str, Any]:
    state = create_initial_state("test-id", query)
    transient_store.register("test-id", EventIDGenerator(), asyncio.Queue())
    return state


@pytest.fixture(autouse=True)
def cleanup():
    yield
    transient_store.unregister("test-id")


@pytest.mark.asyncio
async def test_planner_creates_sub_tasks(mock_planner_response: dict) -> None:
    llm = MockLLMClient(response=mock_planner_response)
    planner = PlannerNode(llm=llm)
    state = _make_state("分析2024年电动汽车电池技术路线对比")

    result = await planner(state)

    assert len(result["sub_tasks"]) == 3
    assert result["sub_tasks"][0]["query"] == "2024年锂电池技术现状和最新进展"
    assert all(t["status"] == "pending" for t in result["sub_tasks"])
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_planner_transitions_to_searching_phase(mock_planner_response: dict) -> None:
    llm = MockLLMClient(response=mock_planner_response)
    planner = PlannerNode(llm=llm)

    result = await planner(_make_state())

    assert result["phase"] == ResearchPhase.SEARCHING.value


@pytest.mark.asyncio
async def test_planner_emits_sse_events_with_required_fields(
    mock_planner_response: dict,
) -> None:
    llm = MockLLMClient(response=mock_planner_response)
    planner = PlannerNode(llm=llm)

    result = await planner(_make_state())

    sse_events = result["_sse_events"]
    assert len(sse_events) >= 2
    assert sse_events[0]["event"] == "phase_change"
    assert sse_events[1]["event"] == "agent_step"

    # Protocol compliance: all events have event_id and timestamp
    for sse in sse_events:
        assert "event_id" in sse["data"]
        assert "timestamp" in sse["data"]
        assert isinstance(sse["data"]["event_id"], int)

    # phase_change must have from_phase
    assert "from_phase" in sse_events[0]["data"]

    # agent_step must have step_id
    assert "step_id" in sse_events[1]["data"]
    assert sse_events[1]["data"]["step_id"].startswith("planner_")


@pytest.mark.asyncio
async def test_planner_event_ids_are_monotonic(mock_planner_response: dict) -> None:
    llm = MockLLMClient(response=mock_planner_response)
    planner = PlannerNode(llm=llm)

    result = await planner(_make_state())

    event_ids = [e["data"]["event_id"] for e in result["_sse_events"]]
    assert event_ids == sorted(event_ids)
    assert len(set(event_ids)) == len(event_ids)  # no duplicates


@pytest.mark.asyncio
async def test_planner_preserves_message_history(mock_planner_response: dict) -> None:
    llm = MockLLMClient(response=mock_planner_response)
    planner = PlannerNode(llm=llm)
    state = _make_state()
    state["messages"] = [{"role": "user", "content": "prior message"}]

    result = await planner(state)

    assert len(result["messages"]) == 2
    assert result["messages"][0]["content"] == "prior message"
