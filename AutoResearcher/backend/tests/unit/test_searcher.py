"""
Unit tests for the Searcher node.
Demonstrates how to mock SearchClient and test search execution + progress tracking.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agent.nodes.searcher import SearcherNode
from app.agent.state import ResearchPhase
from app.models.events import EventIDGenerator


class MockSearchClient:
    """Mock search client with controllable responses."""

    def __init__(
        self,
        results: list[dict[str, Any]] | None = None,
        error: Exception | None = None,
    ):
        self._results = results or [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
                "score": 0.95,
            }
        ]
        self._error = error
        self.call_count = 0
        self.queries: list[str] = []

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        self.call_count += 1
        self.queries.append(query)
        if self._error:
            raise self._error
        return self._results


def _make_state_with_tasks() -> dict[str, Any]:
    return {
        "query": "test query",
        "phase": "planning",
        "sub_tasks": [
            {"id": "task_1", "query": "subtask 1", "status": "pending", "result": None},
            {"id": "task_2", "query": "subtask 2", "status": "pending", "result": None},
        ],
        "search_results": [],
        "_id_gen": EventIDGenerator(),
    }


@pytest.mark.asyncio
async def test_searcher_executes_all_pending_tasks() -> None:
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    assert search.call_count == 2
    assert search.queries == ["subtask 1", "subtask 2"]
    assert len(result["search_results"]) == 2


@pytest.mark.asyncio
async def test_searcher_marks_tasks_completed() -> None:
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    assert all(t["status"] == "completed" for t in result["sub_tasks"])


@pytest.mark.asyncio
async def test_searcher_handles_search_failure() -> None:
    search = MockSearchClient(error=ConnectionError("API timeout"))
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    assert all(t["status"] == "failed" for t in result["sub_tasks"])
    assert len(result["search_results"]) == 0


@pytest.mark.asyncio
async def test_searcher_skips_completed_tasks() -> None:
    state = {
        "query": "test",
        "phase": "planning",
        "sub_tasks": [
            {"id": "task_1", "query": "done", "status": "completed", "result": "ok"},
            {"id": "task_2", "query": "pending", "status": "pending", "result": None},
        ],
        "search_results": [],
        "_id_gen": EventIDGenerator(),
    }
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(state)

    assert search.call_count == 1
    assert search.queries == ["pending"]


@pytest.mark.asyncio
async def test_searcher_emits_progress_events_with_required_fields() -> None:
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    sse_events = result["_sse_events"]
    progress_events = [e for e in sse_events if e.event.value == "progress"]
    assert len(progress_events) == 2
    assert progress_events[0].data["current"] == 1
    assert progress_events[0].data["total"] == 2

    # Protocol compliance
    for sse in sse_events:
        assert "event_id" in sse.data
        assert "timestamp" in sse.data

    # agent_step events must have step_id
    step_events = [e for e in sse_events if e.event.value == "agent_step"]
    for step in step_events:
        assert "step_id" in step.data
        assert step.data["step_id"].startswith("searcher_")


@pytest.mark.asyncio
async def test_searcher_phase_change_includes_from_phase() -> None:
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    phase_events = [e for e in result["_sse_events"] if e.event.value == "phase_change"]
    assert len(phase_events) == 1
    assert phase_events[0].data["from_phase"] == "planning"
    assert phase_events[0].data["phase"] == "searching"


@pytest.mark.asyncio
async def test_searcher_event_ids_are_monotonic() -> None:
    search = MockSearchClient()
    searcher = SearcherNode(search=search)

    result = await searcher(_make_state_with_tasks())

    event_ids = [e.data["event_id"] for e in result["_sse_events"]]
    assert event_ids == sorted(event_ids)
    assert len(set(event_ids)) == len(event_ids)
