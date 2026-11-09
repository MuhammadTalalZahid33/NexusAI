"""Deterministic stub providers for offline development and testing.

- StubEmbeddingProvider: hashes text into a fixed-dim vector. Same text ->
  same vector, and similar texts share tokens so cosine similarity is
  meaningful enough to exercise the retrieval pipeline. No network, no key.
- StubLLMProvider: echoes a templated answer that cites the provided context,
  so citation-validation logic can be tested deterministically.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import AsyncIterator

from app.providers.base import EmbeddingProvider, LLMProvider, RerankerProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        # Bag-of-words hashed into `dim` buckets, then L2-normalized.
        vec = [0.0] * self.dim
        for token in _TOKEN_RE.findall(text.lower()):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class StubRerankerProvider(RerankerProvider):
    """Token-overlap (Jaccard) reranker -- deterministic, offline."""

    async def rerank(
        self, query: str, documents: list[str], top_k: int
    ) -> list[tuple[int, float]]:
        q = set(_TOKEN_RE.findall(query.lower()))
        scored: list[tuple[int, float]] = []
        for i, doc in enumerate(documents):
            d = set(_TOKEN_RE.findall(doc.lower()))
            overlap = len(q & d)
            union = len(q | d) or 1
            scored.append((i, overlap / union))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class StubLLMProvider(LLMProvider):
    async def generate(self, system: str, user: str) -> str:
        # Deterministic: if the prompt contains numbered sources, cite [1].
        if "[1]" in user or "Source 1" in user:
            return "Based on the provided sources, here is the answer [1]."
        return "I don't have enough information to answer that."

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        text = await self.generate(system, user)
        for word in text.split(" "):
            yield word + " "
