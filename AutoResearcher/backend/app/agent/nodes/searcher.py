"""
Searcher node — executes sub-tasks by searching the web via the SearchClient.
"""

from __future__ import annotations

from typing import Any

from app.agent.clients.protocols import SearchClient, VectorStoreClient
from app.agent.state import ResearchPhase, SearchResult, SubTask
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
    def __init__(self, search: SearchClient, vectorstore: VectorStoreClient | None = None):
        self._search = search
        self._vectorstore = vectorstore

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        id_gen: EventIDGenerator = state.get("_id_gen", EventIDGenerator())
        sse_events: list[SSEEvent] = []
        sub_tasks = state.get("sub_tasks", [])
        all_results: list[SearchResult] = list(state.get("search_results", []))
        prev_phase = state.get("phase")

        pending = [t for t in sub_tasks if t["status"] == "pending"]

        retry_count = state.get("retry_count", 0)
        from_phase = (
            ResearchPhase.CRITIQUING.value
            if retry_count > 0
            else ResearchPhase.PLANNING.value
        )

        # Add missing aspects from critique as new sub_tasks on retry
        critique = state.get("critique")
        if critique and retry_count > 0:
            missing_aspects = critique.get("missing_aspects", [])
            for i, aspect in enumerate(missing_aspects):
                new_task_id = f"retry_{retry_count}_task_{i}"
                # Only add if not already present
                if not any(t["id"] == new_task_id for t in sub_tasks):
                    new_task = SubTask(
                        id=new_task_id,
                        query=aspect,
                        status="pending",
                        result=None,
                    )
                    sub_tasks.append(new_task)
                    pending.append(new_task)

        sse_events.append(
            SSEEvent.create(
                SSEEventType.PHASE_CHANGE,
                PhaseChangePayload(
                    phase=ResearchPhase.SEARCHING.value,
                    from_phase=from_phase,
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

        if self._vectorstore and all_results:
            new_results = [r for r in all_results if r not in list(state.get("search_results", []))]
            if new_results:
                try:
                    await self._vectorstore.add_documents(
                        documents=[r["content"] for r in new_results],
                        metadatas=[{"title": r["title"], "url": r["url"], "sub_task_id": r["sub_task_id"]} for r in new_results],
                        ids=[f"search_{state.get('research_id', 'unknown')}_{r['url']}" for r in new_results],
                    )
                except Exception:
                    pass  # vectorstore storage is best-effort

        return {
            "phase": ResearchPhase.CRITIQUING.value,
            "sub_tasks": sub_tasks,
            "search_results": all_results,
            "_sse_events": sse_events,
            "_id_gen": id_gen,
        }
