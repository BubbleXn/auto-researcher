"""
Human feedback node — pauses the workflow via LangGraph interrupt() to collect
user input on the research outline. On resume, interrupt() returns the feedback
value passed via Command(resume=...).
"""

from __future__ import annotations

import time
from typing import Any

from langgraph.types import interrupt

from app.agent.state import ResearchPhase, SubTask
from app.core import transient_store
from app.models.events import (
    HumanInputNeededPayload,
    PhaseChangePayload,
    SSEEvent,
    SSEEventType,
)


class HumanFeedbackNode:
    """Pauses graph execution via interrupt() and waits for human feedback."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        research_id = state["research_id"]
        id_gen = transient_store.get_id_gen(research_id)
        event_queue = transient_store.get_event_queue(research_id)
        is_resume = transient_store.get_is_resume(research_id)

        input_id = f"{research_id}-input-{int(time.time() * 1000)}"

        outline = state.get("plan", {}).get("outline", [])
        outline_payload = [{"section": s, "key_points": []} for s in outline]

        # Only push events on first execution, NOT on resume re-execution
        if event_queue and not is_resume:
            phase_event = SSEEvent.create(
                SSEEventType.PHASE_CHANGE,
                PhaseChangePayload(
                    phase=ResearchPhase.AWAITING_HUMAN_INPUT.value,
                    from_phase=ResearchPhase.CRITIQUING.value,
                    message="等待用户确认研究方案...",
                ),
                id_gen,
            )
            input_event = SSEEvent.create(
                SSEEventType.HUMAN_INPUT_NEEDED,
                HumanInputNeededPayload(
                    input_id=input_id,
                    prompt="请确认以下研究大纲，可以直接修改后提交：",
                    outline=outline_payload,
                    editable_fields=["outline"],
                ),
                id_gen,
            )
            await event_queue.put(phase_event)
            await event_queue.put(input_event)

        feedback_data = interrupt({
            "input_id": input_id,
            "outline": outline_payload,
        })

        # The resume replay ends here: any later pause in this session is a
        # fresh pause and must re-emit its input prompt, otherwise the client
        # would never see a feedback panel again after the first resume.
        transient_store.set_is_resume(research_id, False)

        action: str | None = None
        modified_outline = None
        if isinstance(feedback_data, dict):
            feedback = str(feedback_data.get("feedback") or "")
            modified_outline = feedback_data.get("modified_outline")
            action = feedback_data.get("action")
        else:
            feedback = "" if feedback_data is None else str(feedback_data)

        updated_plan = dict(state.get("plan", {}))
        if modified_outline:
            updated_plan["outline"] = [
                item.get("section", item) if isinstance(item, dict) else item
                for item in modified_outline
            ]

        # Route on the explicit structured action first; fall back to a
        # keyword check for free-form text submitted without an action.
        if action == "more_search" or (action is None and "搜索" in feedback):
            next_phase = ResearchPhase.SEARCHING.value
        else:
            next_phase = ResearchPhase.WRITING.value

        result: dict[str, Any] = {
            "phase": next_phase,
            "human_input_requested": False,
            "human_feedback": feedback or None,
            "plan": updated_plan,
            "_sse_events": [],
            "_last_event_id": id_gen.current,
        }

        if next_phase == ResearchPhase.SEARCHING.value:
            # Seed fresh pending sub-tasks; otherwise SearcherNode finds only
            # completed tasks and spins a round without searching anything.
            sub_tasks = [dict(t) for t in state.get("sub_tasks", [])]
            existing = {str(t.get("query", "")).lower().strip() for t in sub_tasks}
            critique = state.get("critique") or {}
            raw_aspects = critique.get("missing_aspects", [])
            aspects = [
                a.strip()
                for a in (raw_aspects if isinstance(raw_aspects, list) else [])
                if isinstance(a, str) and a.strip()
            ][:3]
            if not aspects and feedback.strip():
                # No critique hints available — search for the user's own words.
                aspects = [feedback.strip()]
            extra = 0
            for aspect in aspects:
                key = aspect.lower()
                if key in existing:
                    continue
                extra += 1
                sub_tasks.append(
                    SubTask(id=f"extra_{extra}", query=aspect, status="pending", result=None)
                )
                existing.add(key)
            result["sub_tasks"] = sub_tasks

        return result
