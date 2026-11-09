"""Token + cost estimation.

Rough per-model pricing (USD per 1M tokens). These are estimates for cost
*awareness* in the demo, not billing. Free-tier usage is $0; the numbers show
what paid usage would cost so the trade-off is visible. Verify against the
provider's live pricing before relying on these.
"""

from __future__ import annotations

# USD per 1M tokens (input, output). Approximate; update from provider pricing.
_PRICING = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-embedding-001": (0.15, 0.0),
    "stub": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    inp, out = _PRICING.get(model, (0.0, 0.0))
    return (input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out
