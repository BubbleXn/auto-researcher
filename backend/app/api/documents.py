"""Document upload API — accepts PDF files, parses and stores in vector store."""
from __future__ import annotations

import asyncio
import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.agent.clients.protocols import VectorStoreClient
from app.core.config import settings
from app.core.dependencies import get_vectorstore_client
from app.models.schemas import DocumentUploadResponse
from app.services.pdf_parser import PDFParser

router = APIRouter(prefix="/api/documents", tags=["documents"])

_pdf_parser = PDFParser()

_MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024
_PDF_MAGIC = b"%PDF"


def _sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from uploaded filename."""
    basename = os.path.basename(filename.replace("\\", "/"))
    basename = re.sub(r"[^\w\-. ]", "_", basename)
    if not basename.lower().endswith(".pdf"):
        basename += ".pdf"
    return basename or "upload.pdf"


def _is_valid_pdf_header(data: bytes) -> bool:
    return data.startswith(_PDF_MAGIC)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    vectorstore: VectorStoreClient = Depends(get_vectorstore_client),
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = _sanitize_filename(file.filename)

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > _MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum upload size of {settings.max_upload_size_mb} MB",
        )
    if not _is_valid_pdf_header(pdf_bytes):
        raise HTTPException(status_code=400, detail="Invalid PDF file header")

    chunks = await asyncio.to_thread(_pdf_parser.parse, pdf_bytes, filename)
    if not chunks:
        raise HTTPException(status_code=422, detail="No text content found in PDF")

    await vectorstore.add_documents(
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
        ids=[c.id for c in chunks],
    )

    return DocumentUploadResponse(
        filename=filename,
        total_chunks=len(chunks),
        total_pages=len(set(c.metadata["page_number"] for c in chunks)),
        document_ids=[c.id for c in chunks],
    )
