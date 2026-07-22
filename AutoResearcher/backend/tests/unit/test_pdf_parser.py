"""Unit tests for PDFParser — creates PDFs in memory, no real files."""
from __future__ import annotations

import pymupdf
import pytest

from app.services.pdf_parser import PDFParser


def _create_pdf(pages: list[str]) -> bytes:
    """Create a PDF in memory with the given page contents."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        rect = page.rect
        rect.x0 += 36
        rect.y0 += 36
        rect.x1 -= 36
        rect.y1 -= 36
        page.insert_textbox(rect, text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestPDFParser:
    def setup_method(self):
        self.parser = PDFParser(chunk_size=100, chunk_overlap=20)

    def test_parse_single_page(self):
        pdf = _create_pdf(["Hello world, this is a test document."])
        chunks = self.parser.parse(pdf, "test.pdf")
        assert len(chunks) >= 1
        assert "Hello world" in chunks[0].text
        assert chunks[0].metadata["source_filename"] == "test.pdf"
        assert chunks[0].metadata["page_number"] == "1"
        assert chunks[0].metadata["source_type"] == "pdf"

    def test_parse_multi_page(self):
        pdf = _create_pdf(["Page one content", "Page two content"])
        chunks = self.parser.parse(pdf, "multi.pdf")
        page_numbers = {c.metadata["page_number"] for c in chunks}
        assert "1" in page_numbers
        assert "2" in page_numbers

    def test_parse_empty_pdf(self):
        doc = pymupdf.open()
        doc.new_page()  # empty page with no text
        pdf_bytes = doc.tobytes()
        doc.close()
        chunks = self.parser.parse(pdf_bytes, "empty.pdf")
        assert len(chunks) == 0

    def test_chunk_ids_unique(self):
        pdf = _create_pdf(["A" * 500])  # long text that will create multiple chunks
        chunks = self.parser.parse(pdf, "long.pdf")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_overlap(self):
        long_text = " ".join(f"word{i}" for i in range(50))
        pdf = _create_pdf([long_text])
        chunks = self.parser.parse(pdf, "overlap.pdf")
        assert len(chunks) >= 2
        if len(chunks) >= 2:
            words_0 = set(chunks[0].text.split())
            words_1 = set(chunks[1].text.split())
            overlap = words_0 & words_1
            assert len(overlap) > 0, "Chunks should share overlapping words"

    def test_metadata_fields_present(self):
        pdf = _create_pdf(["Test content"])
        chunks = self.parser.parse(pdf, "meta.pdf")
        for chunk in chunks:
            assert "source_type" in chunk.metadata
            assert "source_filename" in chunk.metadata
            assert "page_number" in chunk.metadata
            assert "chunk_index" in chunk.metadata
