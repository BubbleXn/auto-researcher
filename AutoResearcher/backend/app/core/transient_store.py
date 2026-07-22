"""Transient (non-serializable) per-session objects for graph node access.

Stores EventIDGenerator and asyncio.Queue that cannot be checkpointed.
Keyed by research_id, set up by research.py before graph execution.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.models.events import EventIDGenerator

_store: dict[str, dict[str, Any]] = {}


def register(research_id: str, id_gen: EventIDGenerator, event_queue: asyncio.Queue) -> None:
    _store[research_id] = {"id_gen": id_gen, "event_queue": event_queue}


def get_id_gen(research_id: str) -> EventIDGenerator:
    entry = _store.get(research_id)
    if entry:
        return entry["id_gen"]
    return EventIDGenerator()


def get_event_queue(research_id: str) -> asyncio.Queue | None:
    entry = _store.get(research_id)
    return entry["event_queue"] if entry else None


def unregister(research_id: str) -> None:
    _store.pop(research_id, None)
