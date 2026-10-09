"""Persistent storage for completed research reports.

Completed sessions are saved to a dedicated SQLite database (separate from
the LangGraph checkpoint store) so the sidebar history and the report page
can list and re-render past research without touching checkpoint blobs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    research_id      TEXT PRIMARY KEY,
    query            TEXT NOT NULL,
    report_markdown  TEXT NOT NULL,
    sources          TEXT NOT NULL,
    total_sources    INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at DESC);
"""


class ReportStore:
    """Async SQLite-backed store for finished research reports."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _require_db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("ReportStore is not connected; call connect() first")
        return self._db

    async def save_report(
        self,
        research_id: str,
        query: str,
        report_markdown: str,
        sources: list[dict[str, Any]],
        duration_seconds: float,
    ) -> None:
        """Insert or replace a finished report (idempotent per research_id)."""
        db = self._require_db()
        await db.execute(
            """
            INSERT OR REPLACE INTO reports
                (research_id, query, report_markdown, sources,
                 total_sources, duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                research_id,
                query,
                report_markdown,
                json.dumps(sources, ensure_ascii=False),
                len(sources),
                duration_seconds,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()

    async def list_reports(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List finished reports, newest first, without the full markdown."""
        db = self._require_db()
        cursor = await db.execute(
            """
            SELECT research_id, query, total_sources, duration_seconds, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_report(self, research_id: str) -> dict[str, Any] | None:
        db = self._require_db()
        cursor = await db.execute(
            """
            SELECT research_id, query, report_markdown, sources,
                   total_sources, duration_seconds, created_at
            FROM reports
            WHERE research_id = ?
            """,
            (research_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        item = dict(row)
        item["sources"] = json.loads(item["sources"])
        return item
