"""PDF parsing service using PyMuPDF."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pymupdf


@dataclass
class TextChunk:
    id: str
    text: str
    metadata: dict[str, str]


class PDFParser:
    """Parse PDF files into overlapping text chunks for vector storage."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def parse(self, pdf_bytes: bytes, filename: str) -> list[TextChunk]:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pages: list[tuple[int, str]] = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append((page_num + 1, text))
        doc.close()
        return self._split_into_chunks(pages, filename)

    def _split_into_chunks(self, pages: list[tuple[int, str]], filename: str) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        chunk_index = 0
        for page_num, text in pages:
            start = 0
            while start < len(text):
                end = start + self._chunk_size
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(TextChunk(
                        id=f"{filename}_p{page_num}_c{chunk_index}",
                        text=chunk_text,
                        metadata={
                            "source_type": "pdf",
                            "source_filename": filename,
                            "page_number": str(page_num),
                            "chunk_index": str(chunk_index),
                        },
                    ))
                    chunk_index += 1
                start += self._chunk_size - self._chunk_overlap
        return chunks
