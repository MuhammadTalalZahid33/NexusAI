"""Hybrid retrieval: vector + keyword -> RRF fusion -> optional rerank.

Pipeline:
  1. Run vector search and keyword search in parallel, each returning a wide
     candidate set (e.g. top 20).
  2. Fuse with Reciprocal Rank Fusion into a single ranking.
  3. Optionally rerank the fused top-N with a cross-encoder for precision.
  4. Return the final top_k.

Each stage is independently testable and the strategy is selectable, so the
evaluation harness can compare vector-only vs hybrid vs hybrid+rerank.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.factory import get_reranker_provider
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.retriever import RetrievedChunk, keyword_retrieve, retrieve

# How many candidates each retriever contributes before fusion/rerank.
CANDIDATE_POOL = 20
# How many fused candidates to feed the reranker.
RERANK_POOL = 20


async def hybrid_retrieve(
    session: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    top_k: int = 5,
    *,
    use_rerank: bool = False,
) -> list[RetrievedChunk]:
    # Run sequentially: a single AsyncSession cannot run concurrent operations
    # (they share one DB connection), so asyncio.gather would error. The cost is
    # negligible -- both are fast indexed lookups.
    vector_hits = await retrieve(session, org_id, query, top_k=CANDIDATE_POOL)
    keyword_hits = await keyword_retrieve(session, org_id, query, top_k=CANDIDATE_POOL)

    fused = reciprocal_rank_fusion([vector_hits, keyword_hits])

    if not use_rerank or not fused:
        return fused[:top_k]

    pool = fused[:RERANK_POOL]
    reranker = get_reranker_provider()
    ranked = await reranker.rerank(query, [c.text for c in pool], top_k=top_k)
    result: list[RetrievedChunk] = []
    for idx, score in ranked:
        chunk = pool[idx]
        chunk.score = score
        result.append(chunk)
    return result
