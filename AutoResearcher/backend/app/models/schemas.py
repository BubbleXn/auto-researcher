"""Request/response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Research question")
    resume_from_event_id: int | None = Field(None, description="For reconnection: last received event_id")


class HumanFeedbackRequest(BaseModel):
    research_id: str
    feedback: str
    modified_outline: list[dict] | None = None


class ResearchStatusResponse(BaseModel):
    research_id: str
    phase: str
    progress: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
