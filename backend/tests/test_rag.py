"""Tests for the baseline RAG pipeline (citation extraction, abstention)."""

from __future__ import annotations

import uuid

from app.retrieval.rag import ABSTAIN_TEXT, _extract_citations
from app.retrieval.retriever import RetrievedChunk


def _chunk(idx: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename=f"doc{idx}.pdf",
        page_number=idx,
        text=f"content {idx}",
        score=1.0,
    )


def test_extract_valid_citations() -> None:
    chunks = [_chunk(1), _chunk(2), _chunk(3)]
    cites = _extract_citations("The answer is X [1] and also Y [3].", chunks)
    assert [c.marker for c in cites] == [1, 3]
    assert cites[0].filename == "doc1.pdf"


def test_fabricated_citation_is_rejected() -> None:
    chunks = [_chunk(1), _chunk(2)]
    # [9] does not exist among 2 sources -> must be dropped.
    cites = _extract_citations("Claim [9].", chunks)
    assert cites == []


def test_duplicate_markers_collapse() -> None:
    chunks = [_chunk(1)]
    cites = _extract_citations("A [1] B [1] C [1]", chunks)
    assert len(cites) == 1


def test_abstain_text_constant() -> None:
    assert "enough information" in ABSTAIN_TEXT
