"""Unit tests for the documents upload API endpoint."""
from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, patch

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_vectorstore_client


class MockVectorStoreClient:
    def __init__(self):
        self.added: list[dict[str, Any]] = []

    async def add_documents(self, documents, metadatas, ids):
        self.added.append({"documents": documents, "metadatas": metadatas, "ids": ids})

    async def query(self, query_text, *, n_results=5, where=None):
        return []

    async def delete(self, ids):
        pass


def _create_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def mock_vectorstore():
    return MockVectorStoreClient()


@pytest.fixture
def client(mock_vectorstore):
    app.dependency_overrides[get_vectorstore_client] = lambda: mock_vectorstore
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestDocumentUpload:
    def test_upload_pdf_success(self, client, mock_vectorstore):
        pdf_bytes = _create_pdf(["Test document content for upload."])
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["total_chunks"] >= 1
        assert data["total_pages"] >= 1
        assert len(data["document_ids"]) >= 1
        assert len(mock_vectorstore.added) == 1

    def test_upload_non_pdf_rejected(self, client):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_empty_file_rejected(self, client):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("empty.pdf", BytesIO(b""), "application/pdf")},
        )
        assert response.status_code == 400

    def test_upload_oversized_file_rejected(self, client):
        with patch("app.api.documents._MAX_UPLOAD_SIZE_BYTES", 10):
            response = client.post(
                "/api/documents/upload",
                files={"file": ("large.pdf", BytesIO(b"x" * 20), "application/pdf")},
            )
        assert response.status_code == 413

    def test_upload_invalid_pdf_header_rejected(self, client):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("fake.pdf", BytesIO(b"not a pdf"), "application/pdf")},
        )
        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    def test_upload_path_traversal_filename_sanitized(self, client, mock_vectorstore):
        pdf_bytes = _create_pdf(["Sanitized filename test."])
        response = client.post(
            "/api/documents/upload",
            files={"file": ("../../etc/passwd.pdf", BytesIO(pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "passwd.pdf"
        assert len(mock_vectorstore.added) == 1
