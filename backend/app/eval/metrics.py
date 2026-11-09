"""Retrieval evaluation metrics.

These are standard IR metrics. Each takes, per query, the ranked list of
retrieved item ids and the set of relevant (ground-truth) ids.

- recall_at_k: fraction of relevant items that appear in the top k.
- reciprocal_rank: 1/rank of the first relevant item (0 if none). MRR is the
  mean of this across queries.
- ndcg_at_k: normalized discounted cumulative gain -- rewards placing relevant
  items higher, with binary relevance here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    return len(top & relevant) / len(relevant)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    dcg = 0.0
    for i, item in enumerate(retrieved[:k], start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(i + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def aggregate(
    per_query_retrieved: list[list[str]],
    per_query_relevant: list[set[str]],
    k: int,
) -> dict[str, float]:
    """Mean metrics across all queries."""
    n = len(per_query_retrieved)
    if n == 0:
        return {f"recall@{k}": 0.0, "mrr": 0.0, f"ndcg@{k}": 0.0}
    recalls = [
        recall_at_k(r, rel, k)
        for r, rel in zip(per_query_retrieved, per_query_relevant, strict=True)
    ]
    rrs = [
        reciprocal_rank(r, rel)
        for r, rel in zip(per_query_retrieved, per_query_relevant, strict=True)
    ]
    ndcgs = [
        ndcg_at_k(r, rel, k)
        for r, rel in zip(per_query_retrieved, per_query_relevant, strict=True)
    ]
    return {
        f"recall@{k}": sum(recalls) / n,
        "mrr": sum(rrs) / n,
        f"ndcg@{k}": sum(ndcgs) / n,
    }
