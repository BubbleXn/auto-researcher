"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.documents import router as documents_router
from app.api.research import router as research_router
from app.core.config import settings
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT_SECONDS = 5.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent SQLite checkpointer for LangGraph."""
    db_path = settings.checkpoint_db_path
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        app.state.checkpointer = checkpointer
        yield


def _chromadb_status() -> str:
    try:
        client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        client.heartbeat()
        return "up"
    except Exception as exc:
        logger.debug("ChromaDB health check failed: %s", exc)
        return "down"


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests with timing, status code, and a unique request ID."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.perf_counter()
    method = request.method
    path = request.url.path

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "request_id=%s method=%s path=%s status=500 duration=%.2fms error=%s",
            request_id,
            method,
            path,
            duration_ms,
            exc,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "request_id=%s method=%s path=%s status=%d duration=%.2fms",
        request_id,
        method,
        path,
        status_code,
        duration_ms,
    )
    return response


app.include_router(research_router)
app.include_router(documents_router)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Docker and monitoring."""
    try:
        chromadb_status = await asyncio.wait_for(
            asyncio.to_thread(_chromadb_status),
            timeout=_HEALTH_CHECK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        chromadb_status = "timeout"

    overall = "healthy" if chromadb_status == "up" else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        services={
            "api": "up",
            "chromadb": chromadb_status,
        },
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
