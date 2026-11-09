"""Tests for evaluation metrics (known hand-computed values)."""

from __future__ import annotations

import math

from app.eval.metrics import aggregate, ndcg_at_k, recall_at_k, reciprocal_rank


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "b", "c"], {"a", "d"}, 3) == 0.5
    assert recall_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
    assert recall_at_k(["x"], {"a"}, 1) == 0.0


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(["x", "a", "y"], {"a"}) == 0.5  # first hit at rank 2
    assert reciprocal_rank(["a"], {"a"}) == 1.0
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_ndcg_at_k_perfect_is_one() -> None:
    assert abs(ndcg_at_k(["a", "b"], {"a", "b"}, 2) - 1.0) < 1e-9


def test_ndcg_rewards_higher_rank() -> None:
    high = ndcg_at_k(["a", "x"], {"a"}, 2)  # relevant at rank 1
    low = ndcg_at_k(["x", "a"], {"a"}, 2)  # relevant at rank 2
    assert high > low
    assert abs(low - (1.0 / math.log2(3))) < 1e-9


def test_aggregate() -> None:
    res = aggregate([["a", "b"], ["x", "a"]], [{"a"}, {"a"}], k=2)
    assert res["mrr"] == (1.0 + 0.5) / 2
    assert res["recall@2"] == 1.0
