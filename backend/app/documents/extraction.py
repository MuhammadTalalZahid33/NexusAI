"""Text extraction from uploaded documents.

Output is a list of `PageText` -- one entry per page, carrying the page number.
Preserving the page boundary is what lets later milestones cite "page N".

Format notes / honest limitations:
- PDF: real page boundaries exist, so page numbers are accurate.
- DOCX: the format has no fixed pages (pagination is decided by the renderer).
  We extract the whole document as a single logical "page" (page_number=None)
  rather than fake page numbers. This is a deliberate, disclosed limitation.
- Scanned/image PDFs: pypdf extracts no text from images. We detect "no text
  extracted" and raise, so ingestion marks the document failed with a clear
  reason instead of silently storing nothing. OCR is an optional later extension.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from docx import Document as DocxDocument
from pypdf import PdfReader


@dataclass
class PageText:
    page_number: int | None
    text: str


class ExtractionError(Exception):
    """Raised when a document cannot be turned into usable text."""


class UnsupportedFileType(ExtractionError):
    pass


def extract_pages(data: bytes, mime_type: str, filename: str) -> list[PageText]:
    """Dispatch to the right extractor based on type. Returns non-empty pages."""
    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        pages = _extract_pdf(data)
    elif (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or filename.lower().endswith(".docx")
    ):
        pages = _extract_docx(data)
    else:
        raise UnsupportedFileType(f"Unsupported file type: {mime_type} ({filename})")

    # Keep only pages that actually contain text.
    non_empty = [p for p in pages if p.text.strip()]
    if not non_empty:
        raise ExtractionError(
            "No extractable text found. The file may be a scanned/image-only "
            "document (OCR is not yet supported) or empty."
        )
    return non_empty


def _extract_pdf(data: bytes) -> list[PageText]:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # malformed/corrupt PDF
        raise ExtractionError(f"Could not read PDF: {exc}") from exc

    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(PageText(page_number=index, text=text))
    return pages


def _extract_docx(data: bytes) -> list[PageText]:
    try:
        doc = DocxDocument(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read DOCX: {exc}") from exc

    # DOCX has no fixed pages; join paragraphs into one logical page.
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return [PageText(page_number=None, text=text)]
