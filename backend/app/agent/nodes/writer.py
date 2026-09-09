"""
Writer node — synthesizes search results into a structured Markdown report.
Uses streaming LLM output to push report_chunk events in real-time via asyncio.Queue.
"""

from __future__ import annotations

from typing import Any

from app.agent.clients.protocols import LLMClient, VectorStoreClient
from app.agent.state import ResearchPhase
from app.core import transient_store
from app.models.events import (
    AgentStepPayload,
    PhaseChangePayload,
    ReportChunkPayload,
    SSEEvent,
    SSEEventType,
    make_step_id,
)

WRITER_SYSTEM_PROMPT = """You are a research report writer. Given a research question,
an outline, and search results, write a comprehensive, well-structured Markdown report.

Requirements:
1. Follow the provided outline structure
2. Cite sources using [Source Title](URL) format
3. Be factual and objective
4. Include a "References" section at the end
5. Write in the same language as the research question"""

CHUNK_FLUSH_SIZE = 150


class WriterNode:
    def __init__(self, llm: LLMClient, vectorstore: VectorStoreClient | None = None):
        self._llm = llm
        self._vectorstore = vectorstore

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        research_id = state["research_id"]
        id_gen = transient_store.get_id_gen(research_id)
        event_queue = transient_store.get_event_queue(research_id)
        sse_events: list[SSEEvent] = []

        phase_event = SSEEvent.create(
            SSEEventType.PHASE_CHANGE,
            PhaseChangePayload(
                phase=ResearchPhase.WRITING.value,
                from_phase=ResearchPhase.AWAITING_HUMAN_INPUT.value,
                message="正在综合信息生成研究报告...",
            ),
            id_gen,
        )
        sse_events.append(phase_event)

        search_context = self._build_context(state)
        outline = state.get("plan", {}).get("outline", [])

        extra_context = ""
        if self._vectorstore:
            try:
                vs_results = await self._vectorstore.query(
                    query_text=state["query"],
                    n_results=10,
                )
                if vs_results:
                    extra_parts = []
                    for r in vs_results:
                        source = r.get("metadata", {}).get("source_filename", "database")
                        extra_parts.append(f"[{source}] {r.get('document', '')[:500]}")
                    extra_context = "\n---\n".join(extra_parts)
            except Exception:
                pass

        user_content = (
            f"Research question: {state['query']}\n\n"
            f"Outline: {outline}\n\n"
            f"Search results:\n{search_context}"
        )
        if extra_context:
            user_content += f"\n\nAdditional reference materials:\n{extra_context}"

        messages = [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_content,
            },
        ]

        step_event = SSEEvent.create(
            SSEEventType.AGENT_STEP,
            AgentStepPayload(
                step_id=make_step_id("writer"),
                node="writer",
                phase=ResearchPhase.WRITING.value,
                action="writing_report",
                detail=f"基于 {len(state.get('search_results', []))} 条搜索结果生成报告",
            ),
            id_gen,
        )
        sse_events.append(step_event)

        report_parts: list[str] = []
        buffer: list[str] = []
        chunk_index = 0

        async for token in self._llm.generate_stream(
            messages, temperature=0.3, max_tokens=8192
        ):
            buffer.append(token)
            if len("".join(buffer)) >= CHUNK_FLUSH_SIZE:
                chunk_text = "".join(buffer)
                buffer = []
                chunk_event = SSEEvent.create(
                    SSEEventType.REPORT_CHUNK,
                    ReportChunkPayload(
                        chunk=chunk_text,
                        chunk_index=chunk_index,
                        is_final=False,
                    ),
                    id_gen,
                )
                if event_queue:
                    await event_queue.put(chunk_event)
                report_parts.append(chunk_text)
                chunk_index += 1

        if buffer:
            chunk_text = "".join(buffer)
            final_event = SSEEvent.create(
                SSEEventType.REPORT_CHUNK,
                ReportChunkPayload(
                    chunk=chunk_text,
                    chunk_index=chunk_index,
                    is_final=True,
                ),
                id_gen,
            )
            if event_queue:
                await event_queue.put(final_event)
            report_parts.append(chunk_text)
        elif report_parts:
            done_event = SSEEvent.create(
                SSEEventType.REPORT_CHUNK,
                ReportChunkPayload(
                    chunk="",
                    chunk_index=chunk_index,
                    is_final=True,
                ),
                id_gen,
            )
            if event_queue:
                await event_queue.put(done_event)

        report = "".join(report_parts)
        sources = self._extract_sources(state)

        return {
            "phase": ResearchPhase.COMPLETED.value,
            "report": report,
            "sources": sources,
            "_sse_events": [e.model_dump(mode="json") for e in sse_events],
            "_last_event_id": id_gen.current,
        }

    @staticmethod
    def _build_context(state: dict[str, Any]) -> str:
        parts: list[str] = []
        for i, result in enumerate(state.get("search_results", []), 1):
            parts.append(
                f"[{i}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Content: {result['content']}\n"
            )
        return "\n---\n".join(parts)

    @staticmethod
    def _extract_sources(state: dict[str, Any]) -> list[dict[str, str]]:
        seen_urls: set[str] = set()
        sources: list[dict[str, str]] = []
        for result in state.get("search_results", []):
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                sources.append(
                    {
                        "title": result["title"],
                        "url": result["url"],
                        "used_in": result["sub_task_id"],
                    }
                )
        return sources
