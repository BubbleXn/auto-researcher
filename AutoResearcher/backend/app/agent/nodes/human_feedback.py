"""
Human feedback node — pauses the workflow via LangGraph interrupt() to collect
user input on the research outline. On resume, interrupt() returns the feedback
value passed via Command(resume=...).
"""

from __future__ import annotations

import time
from typing import Any

from langgraph.types import interrupt

from app.agent.state import ResearchPhase
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

        feedback = feedback_data.get("feedback", "") if isinstance(feedback_data, dict) else str(feedback_data)
        modified_outline = feedback_data.get("modified_outline") if isinstance(feedback_data, dict) else None

        updated_plan = dict(state.get("plan", {}))
        if modified_outline:
            updated_plan["outline"] = [
                item.get("section", item) if isinstance(item, dict) else item
                for item in modified_outline
            ]

        # Route based on feedback: "补充搜索" → back to searcher
        if "搜索" in (feedback or ""):
            next_phase = ResearchPhase.SEARCHING.value
        else:
            next_phase = ResearchPhase.WRITING.value

        return {
            "phase": next_phase,
            "human_input_requested": False,
            "human_feedback": feedback or None,
            "plan": updated_plan,
            "_sse_events": [],
            "_last_event_id": id_gen.current,
        }
