"""Research API routes — SSE streaming with interrupt/resume, reconnection, and human feedback."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.agent.clients.protocols import LLMClient, SearchClient, VectorStoreClient
from app.agent.graph import build_research_graph
from app.agent.state import ResearchPhase, create_initial_state
from app.core import transient_store
from app.core.dependencies import (
    get_llm_client,
    get_search_client,
    get_semaphore,
    get_vectorstore_client,
)
from app.models.events import (
    CompletedStep,
    DonePayload,
    ErrorPayload,
    EventIDGenerator,
    PendingSubTask,
    ResearchStartPayload,
    ResumeStatePayload,
    SSEEvent,
    SSEEventType,
)
from app.models.schemas import HumanFeedbackRequest, ResearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_compiled_graphs: dict[str, Any] = {}
_feedback_futures: dict[str, asyncio.Future] = {}
_active_research: dict[str, dict] = {}


def _get_or_build_graph(
    research_id: str,
    llm: LLMClient,
    search: SearchClient,
    vectorstore: VectorStoreClient,
    checkpointer: Any,
):
    if research_id not in _compiled_graphs:
        _compiled_graphs[research_id] = build_research_graph(
            llm=llm,
            search=search,
            vectorstore=vectorstore,
            checkpointer=checkpointer,
        )
    return _compiled_graphs[research_id]


async def _stream_graph_events(
    graph,
    input_or_command,
    config: dict,
    event_queue: asyncio.Queue,
) -> list:
    """Run graph.astream and drain SSE events into the queue.

    Returns the final sources list. On interrupt, astream ends naturally.
    """
    final_sources: list = []
    try:
        async for event in graph.astream(input_or_command, config=config):
            if "__interrupt__" in event:
                logger.info("Graph interrupted (astream __interrupt__)")
                continue
            for node_name, node_output in event.items():
                for sse_dict in node_output.get("_sse_events", []):
                    sse = SSEEvent.model_validate(sse_dict)
                    await event_queue.put(sse)
                if "sources" in node_output:
                    final_sources = node_output["sources"]
                logger.debug("Node '%s' completed, %d SSE events", node_name, len(node_output.get("_sse_events", [])))
    except Exception:
        logger.exception("Error in _stream_graph_events")
        raise
    finally:
        await event_queue.put(None)
    return final_sources


async def _drain_queue(event_queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE strings from queue until sentinel None."""
    while True:
        sse = await event_queue.get()
        if sse is None:
            break
        yield sse.to_sse()


async def _wait_for_feedback(research_id: str, timeout: float = 15.0) -> AsyncGenerator[dict[str, Any] | None, None]:
    """Wait for human feedback, yielding None on heartbeat intervals."""
    feedback_future: asyncio.Future = asyncio.get_running_loop().create_future()
    _feedback_futures[research_id] = feedback_future
    try:
        while True:
            try:
                data = await asyncio.wait_for(asyncio.shield(feedback_future), timeout=timeout)
                yield data
                return
            except asyncio.TimeoutError:
                yield None
    finally:
        _feedback_futures.pop(research_id, None)


async def _run_research_stream(
    research_id: str,
    query: str,
    llm: LLMClient,
    search: SearchClient,
    vectorstore: VectorStoreClient,
    semaphore: asyncio.Semaphore,
    checkpointer: Any,
    resume_from_event_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Execute the research graph and yield SSE events.

    Handles interrupt/resume loop: when HumanFeedbackNode calls interrupt(),
    astream terminates. We wait for feedback via asyncio.Future, resume
    the graph with Command(resume=data), and continue. This loop repeats
    if the user requests additional searching (feedback routes back to searcher).

    All exit paths (normal completion, error, missing checkpoint, already completed)
    run the same cleanup in the final block.
    """
    start_time = time.time()
    config = {"configurable": {"thread_id": research_id}}
    graph = _get_or_build_graph(research_id, llm, search, vectorstore, checkpointer)

    id_gen: EventIDGenerator
    event_queue: asyncio.Queue[SSEEvent | None]
    input_or_cmd: Any

    try:
        if resume_from_event_id is not None:
            # --- Reconnection ---
            snapshot = await graph.aget_state(config)
            if not snapshot or not snapshot.values:
                yield SSEEvent.create(
                    SSEEventType.ERROR,
                    ErrorPayload(
                        error_code="CHECKPOINT_CORRUPTED",
                        message="No checkpoint found for reconnection",
                        recoverable=False,
                    ),
                    EventIDGenerator(),
                ).to_sse()
                return

            state_vals = snapshot.values
            completed_steps = [
                CompletedStep(
                    step_id=f"resumed_{i}",
                    action="completed",
                    detail=msg.get("content", "")[:100],
                )
                for i, msg in enumerate(state_vals.get("messages", []))
            ]
            pending_sub_tasks = [
                PendingSubTask(id=t["id"], query=t["query"], status=t["status"])
                for t in state_vals.get("sub_tasks", [])
                if t.get("status") == "pending"
            ]

            id_gen = EventIDGenerator(start=state_vals.get("_last_event_id", 0))
            yield SSEEvent.create(
                SSEEventType.RESUME_STATE,
                ResumeStatePayload(
                    research_id=research_id,
                    resumed=True,
                    phase=state_vals.get("phase", "unknown"),
                    retry_count=state_vals.get("retry_count", 0),
                    max_retries=state_vals.get("max_retries", 3),
                    completed_steps=completed_steps,
                    pending_sub_tasks=pending_sub_tasks,
                    report_so_far=state_vals.get("report", ""),
                ),
                id_gen,
            ).to_sse()

            if not snapshot.next:
                # Session already completed; nothing to resume.
                return

            event_queue = asyncio.Queue()
            transient_store.register(research_id, id_gen, event_queue, is_resume=True)
            _active_research[research_id] = {
                "query": state_vals.get("query", ""),
                "phase": state_vals.get("phase", "unknown"),
            }

            async for feedback_data in _wait_for_feedback(research_id):
                if feedback_data is None:
                    yield ": heartbeat\n\n"
                    continue
                break
            input_or_cmd = Command(resume=feedback_data)
        else:
            # --- Normal flow ---
            id_gen = EventIDGenerator()
            event_queue = asyncio.Queue()
            transient_store.register(research_id, id_gen, event_queue)
            _active_research[research_id] = {"query": query, "phase": "planning"}

            yield SSEEvent.create(
                SSEEventType.RESEARCH_START,
                ResearchStartPayload(research_id=research_id, query=query),
                id_gen,
            ).to_sse()
            input_or_cmd = create_initial_state(research_id, query)

        # --- Shared execution loop ---
        async with semaphore:
            while True:
                task = asyncio.create_task(
                    _stream_graph_events(graph, input_or_cmd, config, event_queue)
                )
                async for sse_str in _drain_queue(event_queue):
                    yield sse_str
                final_sources = await task

                snapshot = await graph.aget_state(config)
                if not snapshot.next:
                    break

                # Interrupted — wait for feedback with heartbeat to keep SSE alive
                logger.info("[%s] Graph interrupted, waiting for feedback", research_id)
                async for feedback_data in _wait_for_feedback(research_id):
                    if feedback_data is None:
                        yield ": heartbeat\n\n"
                        continue
                    break
                logger.info("[%s] Feedback received: %s", research_id, feedback_data.get("feedback", "")[:50])

                last_eid = snapshot.values.get("_last_event_id", id_gen.current)
                id_gen = EventIDGenerator(start=last_eid)
                event_queue = asyncio.Queue()
                transient_store.register(research_id, id_gen, event_queue, is_resume=True)
                input_or_cmd = Command(resume=feedback_data)

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
            logger.info("[%s] Research completed in %.1fs", research_id, duration)

    except Exception as e:
        logger.exception("Research stream failed for %s", research_id)
        yield SSEEvent.create(
            SSEEventType.ERROR,
            ErrorPayload(
                error_code="RESEARCH_FAILED",
                message=str(e),
                recoverable=False,
            ),
            id_gen if "id_gen" in locals() else EventIDGenerator(),
        ).to_sse()
    finally:
        _active_research.pop(research_id, None)
        _compiled_graphs.pop(research_id, None)
        transient_store.unregister(research_id)


@router.post("/start")
async def start_research(
    request: Request,
    body: ResearchRequest,
    llm: LLMClient = Depends(get_llm_client),
    search: SearchClient = Depends(get_search_client),
    vectorstore: VectorStoreClient = Depends(get_vectorstore_client),
    semaphore: asyncio.Semaphore = Depends(get_semaphore),
) -> StreamingResponse:
    """Start a research task and stream SSE events."""
    checkpointer = request.app.state.checkpointer
    research_id = body.research_id or str(uuid.uuid4())

    return StreamingResponse(
        _run_research_stream(
            research_id=research_id,
            query=body.query,
            llm=llm,
            search=search,
            vectorstore=vectorstore,
            semaphore=semaphore,
            checkpointer=checkpointer,
            resume_from_event_id=body.resume_from_event_id,
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
    """Submit human feedback for a paused research task.

    Resolves the asyncio.Future that the SSE stream is awaiting,
    which triggers graph resume via Command(resume=data).
    """
    future = _feedback_futures.get(request.research_id)
    if not future:
        logger.warning("Feedback for unknown/non-waiting research: %s", request.research_id)
        return {"status": "error", "message": "Research task not found or not awaiting feedback"}

    feedback_data = {
        "feedback": request.feedback,
        "modified_outline": request.modified_outline,
    }
    future.set_result(feedback_data)
    logger.info("Feedback delivered for %s: %s", request.research_id, request.feedback[:50])

    return {"status": "ok", "research_id": request.research_id}


@router.get("/status/{research_id}")
async def get_status(research_id: str) -> dict:
    """Get the current status of a research task."""
    if research_id not in _active_research:
        return {"status": "not_found"}
    return {"status": "active", **_active_research[research_id]}
