"""Cohere reranker (real API).

Cohere Rerank scores (query, document) pairs with a cross-encoder. The package
is imported lazily so the app runs without it (and without a key) on the stub.

Free trial key: ~1,000 calls/month, ~10 rerank rpm -- enough for eval + demo.
Swappable via the RerankerProvider interface.
"""

from __future__ import annotations

import asyncio

from app.providers.base import RerankerProvider


class CohereRerankerProvider(RerankerProvider):
    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        try:
            import cohere  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("cohere is not installed. Run: pip install cohere") from exc
        self._client = cohere.ClientV2(api_key=api_key)
        self._model = model

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        return await asyncio.to_thread(self._rerank_sync, query, documents, top_k)

    def _rerank_sync(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        resp = self._client.rerank(
            model=self._model,
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
        )
        return [(r.index, float(r.relevance_score)) for r in resp.results]
