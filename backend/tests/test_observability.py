"""Tests for observability metrics + generation-quality metrics + cost."""

from __future__ import annotations

from app.eval.generation_metrics import (
    abstention_correct,
    citation_precision,
    groundedness,
)
from app.observability.cost import estimate_cost
from app.observability.metrics import _percentile, _Registry


def test_percentiles() -> None:
    vals = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert _percentile(vals, 0.5) == 30.0
    assert _percentile([], 0.95) == 0.0


def test_registry_records_and_snapshots() -> None:
    reg = _Registry()
    reg.record_latency("op", 12.0)
    reg.record_latency("op", 24.0)
    reg.incr("calls", 3)
    reg.add_tokens("input", 100)
    reg.add_cost(0.01)
    snap = reg.snapshot()
    assert snap["latency"]["op"]["count"] == 2
    assert snap["counters"]["calls"] == 3
    assert snap["tokens"]["input"] == 100
    assert snap["cost_usd"] == 0.01


def test_groundedness() -> None:
    ctx = ["employees get 25 days of annual leave"]
    high = groundedness("employees get 25 days of leave", ctx)
    low = groundedness("the stock market crashed yesterday", ctx)
    assert high > low
    assert 0.0 <= high <= 1.0


def test_citation_precision() -> None:
    answer = "Employees get 25 days of annual leave [1]."
    good = citation_precision(["employees get 25 days of annual leave"], answer)
    bad = citation_precision(["completely unrelated cooking content"], answer)
    assert good == 1.0
    assert bad == 0.0


def test_abstention_correct() -> None:
    assert abstention_correct(True, True) is True
    assert abstention_correct(False, True) is False


def test_cost_estimate() -> None:
    assert estimate_cost("stub", 1000, 1000) == 0.0
    assert estimate_cost("gemini-2.5-flash", 1_000_000, 0) == 0.30
