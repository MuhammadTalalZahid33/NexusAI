"""Tests for the stub providers + factory fallback."""

from __future__ import annotations

import pytest

from app.providers.stub import StubEmbeddingProvider, StubLLMProvider


@pytest.mark.asyncio
async def test_stub_embedding_deterministic_and_normalized() -> None:
    p = StubEmbeddingProvider(dim=64)
    a = await p.embed_query("hello world")
    b = await p.embed_query("hello world")
    assert a == b  # deterministic
    assert len(a) == 64
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6 or norm == 0.0


@pytest.mark.asyncio
async def test_stub_embedding_similar_texts_closer_than_different() -> None:
    p = StubEmbeddingProvider(dim=256)
    q = await p.embed_query("contract payment terms")
    similar = (await p.embed_documents(["the payment terms of the contract"]))[0]
    different = (await p.embed_documents(["unrelated cooking recipe"]))[0]

    def dot(x, y):
        return sum(a * b for a, b in zip(x, y, strict=True))

    assert dot(q, similar) > dot(q, different)


@pytest.mark.asyncio
async def test_stub_llm_cites_when_sources_present() -> None:
    llm = StubLLMProvider()
    with_sources = await llm.generate("sys", "QUESTION x\n[1] source")
    assert "[1]" in with_sources
    without = await llm.generate("sys", "QUESTION x")
    assert "enough information" in without
