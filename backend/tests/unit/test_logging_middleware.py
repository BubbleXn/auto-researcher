"""Unit tests for the request logging middleware."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_middleware_adds_request_id_header():
    with patch("app.main._chromadb_status", return_value="up"):
        client = TestClient(app)
        response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 8


def test_middleware_logs_request(caplog):
    import logging

    with patch("app.main._chromadb_status", return_value="up"):
        # Adjust the logger level for this test
        logger = logging.getLogger("app.main")
        original_level = logger.level
        logger.setLevel(logging.INFO)
        try:
            client = TestClient(app)
            with caplog.at_level(logging.INFO, logger="app.main"):
                response = client.get("/health")
        finally:
            logger.setLevel(original_level)

    assert response.status_code == 200
    assert any("method=GET path=/health status=200" in record.message for record in caplog.records)
