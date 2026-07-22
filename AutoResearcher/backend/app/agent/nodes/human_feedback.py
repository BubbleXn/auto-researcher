"""
Human feedback node — pauses the workflow to collect user input on the research outline.
Uses asyncio.Event for pause/resume coordination with the feedback API endpoint.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.agent.state import ResearchPhase
from app.core import session_registry
from app.models.events import (
    EventIDGenerator,
    HumanInputNeededPayload,
    PhaseChangePayload,
    SSEEvent,
    SSEEventType,
)


class HumanFeedbackNode:
    """Pauses graph execution and waits for human feedback on the research outline."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        id_gen: EventIDGenerator = state.get("_id_gen", EventIDGenerator())
        event_queue: asyncio.Queue | None = state.get("_event_queue")

        research_id = state["research_id"]
        input_id = f"{research_id}-input-{int(time.time() * 1000)}"

        # Build outline for display from plan
        outline = state.get("plan", {}).get("outline", [])
        outline_payload = [{"section": s, "key_points": []} for s in outline]

        # --- Emit phase change ---
        phase_event = SSEEvent.create(
            SSEEventType.PHASE_CHANGE,
            PhaseChangePayload(
                phase=ResearchPhase.AWAITING_HUMAN_INPUT.value,
                from_phase=ResearchPhase.CRITIQUING.value,
                message="等待用户确认研究方案...",
            ),
            id_gen,
        )

        # --- Emit human_input_needed ---
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

        # Push events immediately via queue so they reach the SSE stream
        if event_queue:
            await event_queue.put(phase_event)
            await event_queue.put(input_event)

        # --- Wait for feedback ---
        feedback_event = asyncio.Event()
        session = session_registry.get_session(research_id)
        session["_feedback_event"] = feedback_event
        session["_input_id"] = input_id

        await feedback_event.wait()

        # --- Retrieve feedback ---
        feedback = session.get("human_feedback", "")
        modified_outline = session.get("modified_outline")

        # Update plan if outline was modified
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
            "_sse_events": [],  # Already pushed via queue
            "_id_gen": id_gen,
        }
