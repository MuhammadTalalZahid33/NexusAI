"""Tests for RRF fusion and the stub reranker."""

from __future__ import annotations

import uuid

import pytest

from app.providers.stub import StubRerankerProvider
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.retriever import RetrievedChunk


def _c(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="d.pdf",
        page_number=1,
        text=text,
        score=0.0,
    )


def test_rrf_rewards_items_high_in_both_lists() -> None:
    a, b, c = _c("a"), _c("b"), _c("c")
    # a is #1 in both lists -> must rank first after fusion.
    vector = [a, b, c]
    keyword = [a, c, b]
    fused = reciprocal_rank_fusion([vector, keyword])
    assert fused[0].chunk_id == a.chunk_id


def test_rrf_includes_items_from_either_list() -> None:
    a, b = _c("a"), _c("b")
    fused = reciprocal_rank_fusion([[a], [b]])
    ids = {c.chunk_id for c in fused}
    assert ids == {a.chunk_id, b.chunk_id}


@pytest.mark.asyncio
async def test_stub_reranker_orders_by_overlap() -> None:
    r = StubRerankerProvider()
    docs = ["completely unrelated text", "payment terms and conditions apply"]
    ranked = await r.rerank("what are the payment terms", docs, top_k=2)
    assert ranked[0][0] == 1  # the payment-terms doc wins
    assert ranked[0][1] >= ranked[1][1]
