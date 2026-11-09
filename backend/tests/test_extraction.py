"""Tests for text extraction (PDF + DOCX)."""

from __future__ import annotations

import io

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.documents.extraction import (
    ExtractionError,
    UnsupportedFileType,
    extract_pages,
)


def _make_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_docx_joins_paragraphs() -> None:
    data = _make_docx(["Hello world.", "Second paragraph."])
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    pages = extract_pages(data, docx_mime, "x.docx")
    assert len(pages) == 1
    assert pages[0].page_number is None
    assert "Hello world." in pages[0].text
    assert "Second paragraph." in pages[0].text


def test_unsupported_type_raises() -> None:
    with pytest.raises(UnsupportedFileType):
        extract_pages(b"irrelevant", "image/png", "photo.png")


def test_empty_or_imageonly_pdf_raises() -> None:
    # A PDF with blank pages (no text layer) simulates a scanned document.
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(ExtractionError):
        extract_pages(buf.getvalue(), "application/pdf", "scan.pdf")
