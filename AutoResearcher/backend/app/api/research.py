"""Research API routes — SSE streaming endpoint, reconnection, and human feedback."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
from app.agent.graph import build_research_graph
from app.agent.state import ResearchPhase, create_initial_state
from app.core.dependencies import (
    get_llm_client,
    get_search_client,
    get_semaphore,
    get_vectorstore_client,
)
from app.core import session_registry
from app.models.events import (
    DonePayload,
    ErrorPayload,
    EventIDGenerator,
    ResearchStartPayload,
    SSEEvent,
    SSEEventType,
)
from app.models.schemas import HumanFeedbackRequest, ResearchRequest

router = APIRouter(prefix="/api/research", tags=["research"])

_active_research: dict[str, dict] = {}


async def _run_research_stream(
    research_id: str,
    query: str,
    llm: LLMClient,
    search: SearchClient,
    vectorstore: VectorStoreClient,
    semaphore: asyncio.Semaphore,
    resume_from_event_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Execute the research graph and yield SSE events.

    Uses an asyncio.Queue so WriterNode can push report_chunk events in real-time
    while the graph is still executing (streaming LLM output).
    """
    start_time = time.time()
    id_gen = EventIDGenerator()
    event_queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    # Initialize session in shared registry
    session_registry.get_session(research_id)

    yield SSEEvent.create(
        SSEEventType.RESEARCH_START,
        ResearchStartPayload(research_id=research_id, query=query),
        id_gen,
    ).to_sse()

    try:
        async with semaphore:
            state = create_initial_state(research_id, query)
            state["_id_gen"] = id_gen
            state["_event_queue"] = event_queue
            graph = build_research_graph(llm=llm, search=search, vectorstore=vectorstore)

            final_sources: list = []

            async def _run_graph() -> None:
                nonlocal final_sources
                try:
                    async for event in graph.astream(state):
                        for node_name, node_output in event.items():
                            for sse in node_output.get("_sse_events", []):
                                await event_queue.put(sse)
                            if "sources" in node_output:
                                final_sources = node_output["sources"]
                finally:
                    await event_queue.put(None)

            graph_task = asyncio.create_task(_run_graph())

            while True:
                sse = await event_queue.get()
                if sse is None:
                    break
                yield sse.to_sse()

            await graph_task

            duration = time.time() - start_time
            yield SSEEvent.create(
                SSEEventType.DONE,
                DonePayload(
                    research_id=research_id,
                    total_sources=len(final_sources),
                    total_duration_seconds=round(duration, 2),
                ),
                id_gen,
            ).to_sse()

    except Exception as e:
        yield SSEEvent.create(
            SSEEventType.ERROR,
            ErrorPayload(
                error_code="RESEARCH_FAILED",
                message=str(e),
                recoverable=False,
            ),
            id_gen,
        ).to_sse()
    finally:
        _active_research.pop(research_id, None)
        session_registry.remove_session(research_id)


@router.post("/start")
async def start_research(
    request: ResearchRequest,
    llm: LLMClient = Depends(get_llm_client),
    search: SearchClient = Depends(get_search_client),
    vectorstore: VectorStoreClient = Depends(get_vectorstore_client),
    semaphore: asyncio.Semaphore = Depends(get_semaphore),
) -> StreamingResponse:
    """Start a research task and stream SSE events."""
    research_id = str(uuid.uuid4())
    _active_research[research_id] = {"query": request.query, "phase": "planning"}

    return StreamingResponse(
        _run_research_stream(
            research_id=research_id,
            query=request.query,
            llm=llm,
            search=search,
            vectorstore=vectorstore,
            semaphore=semaphore,
            resume_from_event_id=request.resume_from_event_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback")
async def submit_feedback(request: HumanFeedbackRequest) -> dict:
    """Submit human feedback for a paused research task."""
    session = session_registry.get_session(request.research_id)
    if not session:
        return {"status": "error", "message": "Research task not found or already completed"}
    session["human_feedback"] = request.feedback
    session["modified_outline"] = request.modified_outline
    feedback_event: asyncio.Event | None = session.get("_feedback_event")
    if feedback_event:
        feedback_event.set()
    return {"status": "ok", "research_id": request.research_id}


@router.get("/status/{research_id}")
async def get_status(research_id: str) -> dict:
    """Get the current status of a research task."""
    if research_id not in _active_research:
        return {"status": "not_found"}
    return {"status": "active", **_active_research[research_id]}
