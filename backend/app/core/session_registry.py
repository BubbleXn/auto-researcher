"""Shared session registry for cross-module access to active research state."""

from __future__ import annotations

from typing import Any

_active_sessions: dict[str, dict[str, Any]] = {}


def get_session(research_id: str) -> dict[str, Any]:
    """Get or create a session dict for the given research_id."""
    return _active_sessions.setdefault(research_id, {})


def remove_session(research_id: str) -> None:
    """Remove a session when research completes or errors out."""
    _active_sessions.pop(research_id, None)


def has_session(research_id: str) -> bool:
    """Check if a session exists."""
    return research_id in _active_sessions
