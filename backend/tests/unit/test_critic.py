"""
Unit tests for the Critic node.
Demonstrates how to mock LLMClient and test state transitions,
SSE event emission, and retry logic.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agent.nodes.critic import CriticNode
from app.agent.state import ResearchPhase
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


def _make_state_with_results() -> dict[str, Any]:
    transient_store.register("test-id", EventIDGenerator(), asyncio.Queue())
    return {
        "research_id": "test-id",
        "query": "test query",
        "phase": "searching",
        "plan": {"outline": ["Section 1", "Section 2"]},
        "sub_tasks": [
            {"id": "task_1", "query": "q1", "status": "completed", "result": "ok"},
            {"id": "task_2", "query": "q2", "status": "completed", "result": "ok"},
        ],
        "search_results": [
            {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1", "score": 0.9, "sub_task_id": "task_1"},
            {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2", "score": 0.8, "sub_task_id": "task_2"},
        ],
        "retry_count": 0,
        "max_retries": 3,
    }


@pytest.fixture(autouse=True)
def cleanup():
    yield
    transient_store.unregister("test-id")


@pytest.mark.asyncio
async def test_critic_passes_with_high_confidence() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": False,
        "conflicts": [],
        "missing_aspects": [],
        "confidence_score": 0.9,
        "recommendation": "proceed",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()

    result = await critic(state)

    assert result["phase"] == ResearchPhase.WRITING.value
    assert result["critique"] is not None
    assert result["critique"]["confidence_score"] == 0.9
    assert result["critique"]["has_conflicts"] is False
    assert result["critique"]["recommendation"] == "proceed"
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_critic_triggers_retry_on_conflict() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": True,
        "conflicts": [
            {"claim_a": "Battery lasts 10 years", "claim_b": "Battery lasts 5 years", "topic": "battery lifespan"}
        ],
        "missing_aspects": ["battery degradation rate"],
        "confidence_score": 0.4,
        "recommendation": "retry_search",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()
    state["retry_count"] = 0

    result = await critic(state)

    assert result["phase"] == ResearchPhase.SEARCHING.value
    assert result["retry_count"] == 1
    assert result["critique"]["has_conflicts"] is True
    assert len(result["critique"]["conflicts"]) == 1
    # Missing aspects should be added as new sub_tasks
    new_tasks = [t for t in result["sub_tasks"] if t["id"].startswith("retry_")]
    assert len(new_tasks) == 1
    assert new_tasks[0]["query"] == "battery degradation rate"
    assert new_tasks[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_critic_emits_max_retries_error() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": True,
        "conflicts": [
            {"claim_a": "A", "claim_b": "B", "topic": "test"}
        ],
        "missing_aspects": ["more info needed"],
        "confidence_score": 0.3,
        "recommendation": "retry_search",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()
    state["retry_count"] = 3
    state["max_retries"] = 3

    result = await critic(state)

    assert result["phase"] == ResearchPhase.ERROR.value
    # Should have an ERROR SSE event
    error_events = [e for e in result["_sse_events"] if e["event"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["data"]["error_code"] == "MAX_RETRIES_EXCEEDED"
    assert error_events[0]["data"]["message"] == "已达最大重试次数，无法解决信息冲突"
    assert error_events[0]["data"]["recoverable"] is False


@pytest.mark.asyncio
async def test_critic_emits_sse_events_with_required_fields() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": True,
        "conflicts": [
            {"claim_a": "X", "claim_b": "Y", "topic": "test"}
        ],
        "missing_aspects": ["aspect1"],
        "confidence_score": 0.5,
        "recommendation": "retry_search",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()

    result = await critic(state)

    sse_events = result["_sse_events"]
    # Should have at least: phase_change, conflict_detected, retry_triggered
    assert len(sse_events) >= 2

    # Find phase_change and agent_step events
    phase_events = [e for e in sse_events if e["event"] == "phase_change"]
    step_events = [e for e in sse_events if e["event"] == "agent_step"]

    assert len(phase_events) >= 1
    assert len(step_events) >= 1

    # Protocol compliance: all events have event_id and timestamp
    for sse in sse_events:
        assert "event_id" in sse["data"]
        assert "timestamp" in sse["data"]
        assert isinstance(sse["data"]["event_id"], int)
        assert isinstance(sse["data"]["timestamp"], str)

    # phase_change must have from_phase
    assert "from_phase" in phase_events[0]["data"]

    # agent_step must have step_id starting with "critic_"
    for step in step_events:
        assert "step_id" in step["data"]
        assert step["data"]["step_id"].startswith("critic_")


@pytest.mark.asyncio
async def test_critic_event_ids_are_monotonic() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": True,
        "conflicts": [
            {"claim_a": "A", "claim_b": "B", "topic": "t"}
        ],
        "missing_aspects": ["missing"],
        "confidence_score": 0.4,
        "recommendation": "retry_search",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()

    result = await critic(state)

    event_ids = [e["data"]["event_id"] for e in result["_sse_events"]]
    assert event_ids == sorted(event_ids)
    assert len(set(event_ids)) == len(event_ids)  # no duplicates


@pytest.mark.asyncio
async def test_critic_resets_failed_subtasks_on_retry() -> None:
    llm = MockLLMClient(response={
        "has_conflicts": False,
        "conflicts": [],
        "missing_aspects": ["new topic"],
        "confidence_score": 0.5,
        "recommendation": "retry_search",
    })
    critic = CriticNode(llm=llm)
    state = _make_state_with_results()
    # Set some sub_tasks to failed
    state["sub_tasks"] = [
        {"id": "task_1", "query": "q1", "status": "completed", "result": "ok"},
        {"id": "task_2", "query": "q2", "status": "failed", "result": "error"},
        {"id": "task_3", "query": "q3", "status": "failed", "result": "timeout"},
    ]
    state["retry_count"] = 1
    state["max_retries"] = 3

    result = await critic(state)

    assert result["phase"] == ResearchPhase.SEARCHING.value
    assert result["retry_count"] == 2

    # Failed tasks should be reset to pending
    task_2 = next(t for t in result["sub_tasks"] if t["id"] == "task_2")
    task_3 = next(t for t in result["sub_tasks"] if t["id"] == "task_3")
    assert task_2["status"] == "pending"
    assert task_3["status"] == "pending"

    # Completed tasks should remain completed
    task_1 = next(t for t in result["sub_tasks"] if t["id"] == "task_1")
    assert task_1["status"] == "completed"

    # New sub_task for missing aspect should be added
    new_tasks = [t for t in result["sub_tasks"] if t["id"].startswith("retry_2_")]
    assert len(new_tasks) == 1
    assert new_tasks[0]["query"] == "new topic"
    assert new_tasks[0]["status"] == "pending"
