"""
Searcher node — executes sub-tasks by searching the web via the SearchClient.
"""

from __future__ import annotations

from typing import Any

from app.agent.clients.protocols import SearchClient
from app.agent.state import ResearchPhase, SearchResult
from app.models.events import (
    AgentStepPayload,
    EventIDGenerator,
    PhaseChangePayload,
    ProgressPayload,
    SSEEvent,
    SSEEventType,
    make_step_id,
)


class SearcherNode:
    def __init__(self, search: SearchClient):
        self._search = search

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        id_gen: EventIDGenerator = state.get("_id_gen", EventIDGenerator())
        sse_events: list[SSEEvent] = []
        sub_tasks = state.get("sub_tasks", [])
        all_results: list[SearchResult] = list(state.get("search_results", []))
        prev_phase = state.get("phase")

        pending = [t for t in sub_tasks if t["status"] == "pending"]

        sse_events.append(
            SSEEvent.create(
                SSEEventType.PHASE_CHANGE,
                PhaseChangePayload(
                    phase=ResearchPhase.SEARCHING.value,
                    from_phase=ResearchPhase.PLANNING.value,
                    message=f"正在搜索 {len(pending)} 个子主题...",
                ),
                id_gen,
            )
        )

        for i, task in enumerate(pending):
            sse_events.append(
                SSEEvent.create(
                    SSEEventType.PROGRESS,
                    ProgressPayload(
                        current=i + 1,
                        total=len(pending),
                        detail=f"搜索: {task['query']}",
                    ),
                    id_gen,
                )
            )

            try:
                results = await self._search.search(
                    query=task["query"], max_results=5
                )
                for r in results:
                    all_results.append(
                        SearchResult(
                            title=r["title"],
                            url=r["url"],
                            content=r["content"],
                            score=r["score"],
                            sub_task_id=task["id"],
                        )
                    )
                task["status"] = "completed"
                task["result"] = f"Found {len(results)} results"
            except Exception as e:
                task["status"] = "failed"
                task["result"] = str(e)

            sse_events.append(
                SSEEvent.create(
                    SSEEventType.AGENT_STEP,
                    AgentStepPayload(
                        step_id=make_step_id("searcher"),
                        node="searcher",
                        phase=ResearchPhase.SEARCHING.value,
                        action="search_completed",
                        detail=f"子任务 '{task['query']}' — {task['status']}",
                    ),
                    id_gen,
                )
            )

        return {
            "phase": ResearchPhase.WRITING.value,
            "sub_tasks": sub_tasks,
            "search_results": all_results,
            "_sse_events": sse_events,
            "_id_gen": id_gen,
        }
