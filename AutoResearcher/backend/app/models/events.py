"""SSE event models. Defines the contract between backend and frontend.

Aligned with docs/sse-event-protocol.md (9 event types).
All payloads include event_id (incrementing int) and timestamp (ISO 8601 UTC).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """All SSE event types — 9 total, per protocol document."""

    RESEARCH_START = "research_start"
    PHASE_CHANGE = "phase_change"
    AGENT_STEP = "agent_step"
    PROGRESS = "progress"
    HUMAN_INPUT_NEEDED = "human_input_needed"
    REPORT_CHUNK = "report_chunk"
    ERROR = "error"
    DONE = "done"
    RESUME_STATE = "resume_state"


class EventIDGenerator:
    """Thread-safe monotonic event_id counter, one per research session."""

    def __init__(self, start: int = 0) -> None:
        self._counter = start

    def next(self) -> int:
        self._counter += 1
        return self._counter

    @property
    def current(self) -> int:
        return self._counter


# --- Payload models (all include base fields via SSEEvent wrapper) ---


class ResearchStartPayload(BaseModel):
    research_id: str
    query: str


class PhaseChangePayload(BaseModel):
    phase: str
    from_phase: str | None = None
    message: str


class AgentStepPayload(BaseModel):
    step_id: str
    node: str
    phase: str
    action: str
    detail: str
    intermediate_result: dict[str, Any] | None = None


class ProgressPayload(BaseModel):
    current: int
    total: int
    detail: str


class HumanInputNeededPayload(BaseModel):
    input_id: str
    prompt: str
    outline: list[dict[str, Any]]
    editable_fields: list[str]


class ReportChunkPayload(BaseModel):
    chunk: str
    chunk_index: int
    is_final: bool = False


class ErrorPayload(BaseModel):
    error_code: str
    message: str
    recoverable: bool
    detail: str | None = None


class DonePayload(BaseModel):
    research_id: str
    total_sources: int
    total_duration_seconds: float


class CompletedStep(BaseModel):
    step_id: str
    action: str
    detail: str


class PendingSubTask(BaseModel):
    id: str
    query: str
    status: str


class ResumeStatePayload(BaseModel):
    research_id: str
    resumed: bool = True
    phase: str
    retry_count: int = 0
    max_retries: int = 3
    completed_steps: list[CompletedStep]
    pending_sub_tasks: list[PendingSubTask]
    report_so_far: str = ""


class SSEEvent(BaseModel):
    """Wrapper for all SSE events sent to the frontend."""

    event: SSEEventType
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Format as SSE wire protocol."""
        import json

        return f"event: {self.event.value}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"

    @classmethod
    def create(
        cls,
        event_type: SSEEventType,
        payload: BaseModel,
        id_gen: EventIDGenerator,
    ) -> SSEEvent:
        """Create an SSEEvent with auto-populated event_id and timestamp."""
        data = payload.model_dump()
        data["event_id"] = id_gen.next()
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return cls(event=event_type, data=data)


def make_step_id(node_name: str) -> str:
    """Generate unique step_id: {node_name}_{timestamp_ms}."""
    return f"{node_name}_{int(time.time() * 1000)}"
