"""Integration tests for the history/report API endpoints."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api.research import router as research_router
from app.core.dependencies import get_report_store
from app.core.report_store import ReportStore


@pytest.fixture
async def client(tmp_path):
    store = ReportStore(str(tmp_path / "reports.db"))
    await store.connect()
    app = FastAPI()
    app.include_router(research_router)
    app.dependency_overrides[get_report_store] = lambda: store
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, store
    await store.close()


async def test_history_lists_and_returns_report(client) -> None:
    http, store = client
    await store.save_report(
        research_id="hist-1",
        query="量子计算现状",
        report_markdown="# 量子计算报告",
        sources=[{"title": "T", "url": "https://example.com", "content": "c", "score": 0.9}],
        duration_seconds=8.8,
    )

    resp = await http.get("/api/research/history")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["research_id"] == "hist-1"
    assert items[0]["query"] == "量子计算现状"
    assert items[0]["total_sources"] == 1
    assert "report_markdown" not in items[0]

    detail_resp = await http.get("/api/research/history/hist-1/report")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["report_markdown"] == "# 量子计算报告"
    assert detail["query"] == "量子计算现状"
    assert detail["sources"][0]["url"] == "https://example.com"


async def test_report_detail_404_for_unknown_id(client) -> None:
    http, _ = client
    resp = await http.get("/api/research/history/missing/report")
    assert resp.status_code == 404


async def test_history_empty_returns_empty_list(client) -> None:
    http, _ = client
    resp = await http.get("/api/research/history")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_history_rejects_invalid_pagination(client) -> None:
    http, _ = client
    resp = await http.get("/api/research/history", params={"limit": 0})
    assert resp.status_code == 422
    resp = await http.get("/api/research/history", params={"offset": -1})
    assert resp.status_code == 422
