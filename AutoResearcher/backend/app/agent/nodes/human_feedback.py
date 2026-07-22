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

        input_id = f"{research_id}-input-{int(time.time() * 1000)}"

        outline = state.get("plan", {}).get("outline", [])
        outline_payload = [{"section": s, "key_points": []} for s in outline]

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

        # Push events via queue (only on first execution; on resume event_queue is None)
        if event_queue:
            await event_queue.put(phase_event)
            await event_queue.put(input_event)

        # interrupt() raises GraphInterrupt on first call, halting execution.
        # On resume via Command(resume=value), the node re-executes from the top;
        # event_queue will be None (transient_store cleared between runs),
        # so events are skipped. interrupt() returns the resume value immediately.
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

        return {
            "phase": ResearchPhase.WRITING.value,
            "human_input_requested": False,
            "human_feedback": feedback or None,
            "plan": updated_plan,
            "_sse_events": [],
            "_last_event_id": id_gen.current,
        }
