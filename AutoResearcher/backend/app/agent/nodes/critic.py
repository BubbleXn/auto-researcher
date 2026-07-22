"""
Critic node — evaluates search results for conflicts, missing aspects,
and assigns a confidence score. Can trigger retry loops back to Searcher.
"""

from __future__ import annotations

from typing import Any

from app.agent.clients.protocols import LLMClient
from app.agent.state import CritiqueResult, ResearchPhase, SubTask
from app.models.events import (
    AgentStepPayload,
    ErrorPayload,
    EventIDGenerator,
    PhaseChangePayload,
    SSEEvent,
    SSEEventType,
    make_step_id,
)

CRITIC_SYSTEM_PROMPT = """You are a research quality critic. Given a research outline and search results,
evaluate the information for:

1. **Conflicts**: Are there contradictory claims across sources? Identify specific conflicts.
2. **Missing aspects**: Are there sections of the outline that lack sufficient evidence?
3. **Confidence score**: Overall confidence in the collected information (0.0 to 1.0).
4. **Recommendation**: Should the research proceed to writing or retry searching?

Respond in JSON format:
{
    "has_conflicts": true/false,
    "conflicts": [
        {"claim_a": "...", "claim_b": "...", "topic": "..."}
    ],
    "missing_aspects": ["aspect that needs more research", ...],
    "confidence_score": 0.85,
    "recommendation": "proceed" or "retry_search"
}

Rules:
- If confidence_score >= 0.7 and no critical conflicts, recommend "proceed"
- If confidence_score < 0.7 or there are unresolvable conflicts, recommend "retry_search"
- Always provide actionable missing_aspects when recommending retry_search"""


class CriticNode:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        id_gen: EventIDGenerator = state.get("_id_gen", EventIDGenerator())
        sse_events: list[SSEEvent] = []

        # --- Phase change event ---
        sse_events.append(
            SSEEvent.create(
                SSEEventType.PHASE_CHANGE,
                PhaseChangePayload(
                    phase=ResearchPhase.CRITIQUING.value,
                    from_phase=ResearchPhase.SEARCHING.value,
                    message="正在验证信息准确性...",
                ),
                id_gen,
            )
        )

        # --- Build context for the LLM ---
        search_results = state.get("search_results", [])
        outline = state.get("plan", {}).get("outline", [])

        results_context = self._build_results_context(search_results)
        outline_context = "\n".join(f"- {section}" for section in outline)

        messages = [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Research outline:\n{outline_context}\n\n"
                    f"Search results:\n{results_context}"
                ),
            },
        ]

        # --- Call LLM ---
        result = await self._llm.generate_structured(
            messages, schema={"type": "object"}
        )

        # --- Parse into CritiqueResult ---
        critique: CritiqueResult = CritiqueResult(
            has_conflicts=result.get("has_conflicts", False),
            conflicts=result.get("conflicts", []),
            missing_aspects=result.get("missing_aspects", []),
            confidence_score=result.get("confidence_score", 0.0),
            recommendation=result.get("recommendation", "proceed"),
        )

        # --- Emit conflict detection event ---
        if critique["has_conflicts"]:
            conflict_details = "; ".join(
                f"{c.get('topic', '未知主题')}: {c.get('claim_a', '')} vs {c.get('claim_b', '')}"
                for c in critique["conflicts"]
            )
            sse_events.append(
                SSEEvent.create(
                    SSEEventType.AGENT_STEP,
                    AgentStepPayload(
                        step_id=make_step_id("critic"),
                        node="critic",
                        phase=ResearchPhase.CRITIQUING.value,
                        action="conflict_detected",
                        detail=f"发现信息冲突: {conflict_details}",
                    ),
                    id_gen,
                )
            )

        # --- Determine next phase based on recommendation ---
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        sub_tasks = list(state.get("sub_tasks", []))

        if critique["recommendation"] == "proceed":
            next_phase = ResearchPhase.WRITING.value
        elif critique["recommendation"] == "retry_search" and retry_count < max_retries:
            next_phase = ResearchPhase.SEARCHING.value
            retry_count += 1

            # Emit retry event
            missing_desc = ", ".join(critique["missing_aspects"]) if critique["missing_aspects"] else "需要更多信息"
            sse_events.append(
                SSEEvent.create(
                    SSEEventType.AGENT_STEP,
                    AgentStepPayload(
                        step_id=make_step_id("critic"),
                        node="critic",
                        phase=ResearchPhase.CRITIQUING.value,
                        action="retry_triggered",
                        detail=f"需要重新搜索: {missing_desc}",
                    ),
                    id_gen,
                )
            )

            # Reset failed sub_tasks back to pending
            for task in sub_tasks:
                if task["status"] == "failed":
                    task["status"] = "pending"

            # Add missing aspects as new sub_tasks
            for i, aspect in enumerate(critique["missing_aspects"]):
                sub_tasks.append(
                    SubTask(
                        id=f"retry_{retry_count}_task_{i}",
                        query=aspect,
                        status="pending",
                        result=None,
                    )
                )
        else:
            # retry_search but max retries exceeded
            next_phase = ResearchPhase.ERROR.value
            sse_events.append(
                SSEEvent.create(
                    SSEEventType.ERROR,
                    ErrorPayload(
                        error_code="MAX_RETRIES_EXCEEDED",
                        message="已达最大重试次数，无法解决信息冲突",
                        recoverable=False,
                    ),
                    id_gen,
                )
            )

        return {
            "phase": next_phase,
            "critique": critique,
            "retry_count": retry_count,
            "sub_tasks": sub_tasks,
            "_sse_events": sse_events,
            "_id_gen": id_gen,
        }

    @staticmethod
    def _build_results_context(search_results: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for i, result in enumerate(search_results, 1):
            parts.append(
                f"[{i}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Content: {result['content']}\n"
                f"Relevance: {result.get('score', 'N/A')}"
            )
        return "\n---\n".join(parts)
