"""
Planner node — decomposes user query into searchable sub-tasks.
"""

from __future__ import annotations

import json
from typing import Any

from app.agent.clients.protocols import LLMClient
from app.agent.state import ResearchPhase, SubTask
from app.core import transient_store
from app.models.events import (
    AgentStepPayload,
    PhaseChangePayload,
    SSEEvent,
    SSEEventType,
    make_step_id,
)

PLANNER_SYSTEM_PROMPT = """You are a research planning assistant. Given a research question,
decompose it into 3-5 specific, searchable sub-questions that together would provide
a comprehensive answer.

Respond in JSON format:
{
    "outline": ["Section 1 title", "Section 2 title", ...],
    "sub_tasks": [
        {"id": "task_1", "query": "specific search query 1"},
        {"id": "task_2", "query": "specific search query 2"},
        ...
    ]
}"""


class PlannerNode:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        id_gen = transient_store.get_id_gen(state["research_id"])
        sse_events: list[SSEEvent] = []

        sse_events.append(
            SSEEvent.create(
                SSEEventType.PHASE_CHANGE,
                PhaseChangePayload(
                    phase=ResearchPhase.PLANNING.value,
                    from_phase=None,
                    message="正在分析问题并制定研究计划...",
                ),
                id_gen,
            )
        )

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": state["query"]},
        ]

        result = await self._llm.generate_structured(
            messages, schema={"type": "object"}
        )

        sub_tasks: list[SubTask] = []
        for task_data in result.get("sub_tasks", []):
            sub_tasks.append(
                SubTask(
                    id=task_data["id"],
                    query=task_data["query"],
                    status="pending",
                    result=None,
                )
            )

        sse_events.append(
            SSEEvent.create(
                SSEEventType.AGENT_STEP,
                AgentStepPayload(
                    step_id=make_step_id("planner"),
                    node="planner",
                    phase=ResearchPhase.PLANNING.value,
                    action="plan_created",
                    detail=f"已生成 {len(sub_tasks)} 个子研究任务",
                    intermediate_result={"outline": result.get("outline", [])},
                ),
                id_gen,
            )
        )

        return {
            "phase": ResearchPhase.SEARCHING.value,
            "plan": result,
            "sub_tasks": sub_tasks,
            "messages": state.get("messages", [])
            + [{"role": "assistant", "content": json.dumps(result, ensure_ascii=False)}],
            "_sse_events": [e.model_dump(mode="json") for e in sse_events],
            "_last_event_id": id_gen.current,
        }
