"""Unit tests for the health check endpoint."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    yield TestClient(app)


@pytest.mark.parametrize(
    ("chromadb_status", "expected_status", "expected_overall"),
    [
        ("up", "up", "healthy"),
        ("down", "down", "degraded"),
        ("timeout", "timeout", "degraded"),
    ],
)
def test_health_returns_chromadb_status(client, chromadb_status, expected_status, expected_overall):
    with patch("app.main._chromadb_status", return_value=chromadb_status):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == expected_overall
    assert data["version"] == "0.1.0"
    assert data["services"]["api"] == "up"
    assert data["services"]["chromadb"] == expected_status
