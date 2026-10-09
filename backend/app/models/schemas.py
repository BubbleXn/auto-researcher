"""Request/response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Research question")
    resume_from_event_id: int | None = Field(None, description="For reconnection: last received event_id")
    research_id: str | None = Field(None, description="For reconnection: existing research session ID")


class HumanFeedbackRequest(BaseModel):
    research_id: str
    feedback: str
    modified_outline: list[dict] | None = None
    input_id: str | None = None
    action: str | None = Field(
        None,
        description="Structured routing hint: 'proceed' or 'more_search'. "
        "When absent, routing falls back to keyword matching on feedback text.",
    )


class ResearchStatusResponse(BaseModel):
    research_id: str
    phase: str
    progress: str
    error: str | None = None


class HistoryItem(BaseModel):
    """Summary entry for the sidebar history list (no report body)."""

    research_id: str
    query: str
    total_sources: int
    duration_seconds: float
    created_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class ReportDetailResponse(BaseModel):
    research_id: str
    query: str
    report_markdown: str
    sources: list[dict]
    total_sources: int
    duration_seconds: float
    created_at: str


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class DocumentUploadResponse(BaseModel):
    filename: str
    total_chunks: int
    total_pages: int
    document_ids: list[str]
