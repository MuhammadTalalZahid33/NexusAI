"""Tests for the chunking module."""

from __future__ import annotations

import pytest

from app.documents.chunking import chunk_pages, count_tokens
from app.documents.extraction import PageText


def test_short_text_is_single_chunk() -> None:
    pages = [PageText(page_number=1, text="A short sentence.")]
    chunks = chunk_pages(pages, chunk_size_tokens=400, chunk_overlap_tokens=60)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count > 0


def test_long_text_splits_into_multiple_chunks() -> None:
    # ~120 sentences -> well over a small chunk size.
    body = " ".join(f"Sentence number {i} about topic {i}." for i in range(120))
    pages = [PageText(page_number=1, text=body)]
    chunks = chunk_pages(pages, chunk_size_tokens=50, chunk_overlap_tokens=10)
    assert len(chunks) > 1
    # No chunk should greatly exceed the target size.
    for c in chunks:
        assert c.token_count <= 70  # size + a small boundary slack


def test_chunk_indices_are_sequential_across_pages() -> None:
    body = " ".join(f"Sentence {i}." for i in range(80))
    pages = [
        PageText(page_number=1, text=body),
        PageText(page_number=2, text=body),
    ]
    chunks = chunk_pages(pages, chunk_size_tokens=40, chunk_overlap_tokens=8)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
    # Page numbers are preserved.
    assert any(c.page_number == 1 for c in chunks)
    assert any(c.page_number == 2 for c in chunks)


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_pages([PageText(1, "x")], chunk_size_tokens=50, chunk_overlap_tokens=50)


def test_count_tokens_nonzero() -> None:
    assert count_tokens("hello world") >= 2
