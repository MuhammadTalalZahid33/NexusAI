"""Tests for the agentic workflow's bounded logic (no DB needed)."""

from __future__ import annotations

import pytest

from app.agent import nodes
from app.agent.graph import _route_after_assess


def test_strategy_escalation_ladder() -> None:
    assert nodes._next_strategy("vector") == "hybrid"
    assert nodes._next_strategy("hybrid") == "hybrid_rerank"
    # Top of the ladder stays put (cannot escalate further).
    assert nodes._next_strategy("hybrid_rerank") == "hybrid_rerank"


def test_route_generates_when_sufficient() -> None:
    assert _route_after_assess({"sufficient": True, "attempts": 1}) == "generate"


def test_route_escalates_when_insufficient_within_budget() -> None:
    assert _route_after_assess({"sufficient": False, "attempts": 1}) == "escalate"


def test_route_gives_up_after_max_attempts() -> None:
    state = {"sufficient": False, "attempts": nodes.MAX_ATTEMPTS}
    # Exhausted retries -> generate (which abstains honestly if weak).
    assert _route_after_assess(state) == "generate"


@pytest.mark.asyncio
async def test_classify_sets_initial_state() -> None:
    state = await nodes.classify({"question": "What is the leave policy?", "trace": []})
    assert state["strategy"] == "hybrid_rerank"
    assert state["attempts"] == 0
    assert state["query"] == "What is the leave policy?"
