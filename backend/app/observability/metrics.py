"""In-process operational metrics (latency, tokens, cost, errors).

Deliberately lightweight: a thread-safe in-memory registry with percentiles,
exposed via a /metrics endpoint. For a portfolio project this demonstrates the
concepts (p50/p95 latency, token + cost accounting, error counts) without the
operational weight of Prometheus/OpenTelemetry collectors -- which would be the
documented production upgrade path.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


@dataclass
class _Registry:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    latencies_ms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tokens: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cost_usd: float = 0.0

    def record_latency(self, name: str, ms: float) -> None:
        with self._lock:
            self.latencies_ms[name].append(ms)

    def incr(self, name: str, by: int = 1) -> None:
        with self._lock:
            self.counters[name] += by

    def add_tokens(self, kind: str, n: int) -> None:
        with self._lock:
            self.tokens[kind] += n

    def add_cost(self, usd: float) -> None:
        with self._lock:
            self.cost_usd += usd

    def snapshot(self) -> dict:
        with self._lock:
            latency_summary = {
                name: {
                    "count": len(vals),
                    "p50_ms": round(_percentile(vals, 0.50), 2),
                    "p95_ms": round(_percentile(vals, 0.95), 2),
                }
                for name, vals in self.latencies_ms.items()
            }
            return {
                "latency": latency_summary,
                "counters": dict(self.counters),
                "tokens": dict(self.tokens),
                "cost_usd": round(self.cost_usd, 6),
            }

    def reset(self) -> None:
        with self._lock:
            self.latencies_ms.clear()
            self.counters.clear()
            self.tokens.clear()
            self.cost_usd = 0.0


REGISTRY = _Registry()


@contextmanager
def track_latency(name: str):
    """Context manager to record the wall-clock latency of a block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        REGISTRY.record_latency(name, (time.perf_counter() - start) * 1000)
