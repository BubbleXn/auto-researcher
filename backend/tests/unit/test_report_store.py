"""Unit tests for the ReportStore (completed research persistence)."""

from __future__ import annotations

import asyncio

import pytest

from app.core.report_store import ReportStore


@pytest.fixture
async def store(tmp_path):
    store = ReportStore(str(tmp_path / "reports.db"))
    await store.connect()
    yield store
    await store.close()


async def test_save_and_get_report(store) -> None:
    await store.save_report(
        research_id="r1",
        query="测试问题",
        report_markdown="# 报告",
        sources=[{"title": "T", "url": "https://example.com"}],
        duration_seconds=12.5,
    )

    detail = await store.get_report("r1")
    assert detail is not None
    assert detail["query"] == "测试问题"
    assert detail["report_markdown"] == "# 报告"
    assert detail["total_sources"] == 1
    assert detail["duration_seconds"] == 12.5
    assert detail["sources"][0]["url"] == "https://example.com"
    assert detail["created_at"]


async def test_get_report_missing_returns_none(store) -> None:
    assert await store.get_report("nope") is None


async def test_upsert_replaces_existing(store) -> None:
    await store.save_report("r1", "old query", "old", [], 1.0)
    await store.save_report("r1", "new query", "new report", [{"title": "x", "url": "u"}], 2.0)

    detail = await store.get_report("r1")
    assert detail["query"] == "new query"
    assert detail["report_markdown"] == "new report"
    assert detail["total_sources"] == 1


async def test_list_reports_newest_first(store) -> None:
    await store.save_report("r1", "q1", "m1", [], 1.0)
    await asyncio.sleep(0.001)  # ensure distinct created_at timestamps
    await store.save_report("r2", "q2", "m2", [], 2.0)

    items = await store.list_reports()
    assert [i["research_id"] for i in items] == ["r2", "r1"]
    # The list endpoint must stay light: no report bodies.
    assert "report_markdown" not in items[0]


async def test_list_reports_pagination(store) -> None:
    for i in range(5):
        await store.save_report(f"r{i}", f"q{i}", "m", [], 1.0)
        await asyncio.sleep(0.001)

    page = await store.list_reports(limit=2, offset=2)
    assert len(page) == 2
    assert [i["research_id"] for i in page] == ["r2", "r1"]
