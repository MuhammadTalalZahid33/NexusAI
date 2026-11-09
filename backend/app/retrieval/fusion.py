"""Reciprocal Rank Fusion (RRF) for combining ranked lists.

RRF merges multiple rankings (here: vector + keyword) without needing their
scores to be on the same scale -- it uses only rank positions. Each item gets
sum over lists of 1 / (k + rank). The constant k (default 60, the value from
the original RRF paper) dampens the influence of very high ranks.

Why RRF over score-weighting: vector cosine scores and ts_rank scores are not
comparable numerically. Rank-based fusion sidesteps that entirely and is a
robust, widely-used hybrid-search baseline.
"""

from __future__ import annotations

from app.retrieval.retriever import RetrievedChunk

RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    k: int = RRF_K,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Fuse multiple ranked lists into one by RRF score."""
    scores: dict[str, float] = {}
    best: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            key = str(chunk.chunk_id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            # Keep one representative object per chunk.
            best.setdefault(key, chunk)

    fused = sorted(best.values(), key=lambda c: scores[str(c.chunk_id)], reverse=True)
    # Overwrite score with the fused RRF score for transparency downstream.
    for c in fused:
        c.score = scores[str(c.chunk_id)]
    return fused[:top_k] if top_k else fused
