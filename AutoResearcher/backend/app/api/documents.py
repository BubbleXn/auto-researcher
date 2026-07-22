"""Document upload API — accepts PDF files, parses and stores in vector store."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.agent.clients.protocols import VectorStoreClient
from app.core.dependencies import get_vectorstore_client
from app.models.schemas import DocumentUploadResponse
from app.services.pdf_parser import PDFParser

router = APIRouter(prefix="/api/documents", tags=["documents"])

_pdf_parser = PDFParser()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    vectorstore: VectorStoreClient = Depends(get_vectorstore_client),
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    chunks = _pdf_parser.parse(pdf_bytes, file.filename)
    if not chunks:
        raise HTTPException(status_code=422, detail="No text content found in PDF")

    await vectorstore.add_documents(
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
        ids=[c.id for c in chunks],
    )

    return DocumentUploadResponse(
        filename=file.filename,
        total_chunks=len(chunks),
        total_pages=len(set(c.metadata["page_number"] for c in chunks)),
        document_ids=[c.id for c in chunks],
    )
