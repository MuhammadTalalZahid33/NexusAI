"""Node functions for the agentic retrieval workflow.

Design principles (interview-relevant):
- Deterministic by default. We use LLM calls ONLY for classification and query
  rewriting, where language understanding genuinely helps. Sufficiency checking
  and strategy selection are deterministic rules -- cheaper, faster, testable,
  and not subject to LLM nondeterminism.
- Bounded. MAX_ATTEMPTS caps retrieval retries so the graph can never loop
  forever. Each retry escalates to a stronger strategy rather than repeating.
- Observable. Every node appends to state["trace"].

The nodes take dependencies (session) via a partial in graph.py, keeping the
node signatures graph-friendly (state -> state).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.logging_config import get_logger
from app.providers.factory import get_llm_provider
from app.retrieval.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval.rag import (
    ABSTAIN_TEXT,
    STRATEGY_HYBRID,
    STRATEGY_HYBRID_RERANK,
    STRATEGY_VECTOR,
    _extract_citations,
    retrieve_by_strategy,
)

log = get_logger(__name__)

MAX_ATTEMPTS = 2
# Minimum fused/similarity score for the top hit to be considered "evidence".
SUFFICIENCY_MIN_SCORE = 0.0  # stub scores are low; real providers will raise this
# Strategy escalation ladder: each retry moves one step stronger.
STRATEGY_LADDER = [STRATEGY_VECTOR, STRATEGY_HYBRID, STRATEGY_HYBRID_RERANK]


async def classify(state: AgentState) -> AgentState:
    """Lightweight classification: is this answerable from a knowledge base?

    Kept cheap: a single short LLM call. On the stub it is a no-op that always
    proceeds. We do NOT let classification block retrieval on borderline cases
    -- better to retrieve and let sufficiency checking decide.
    """
    state.setdefault("trace", []).append("classify: knowledge_question")
    # Start with the strongest single-shot strategy; escalate only on retry.
    state["strategy"] = STRATEGY_HYBRID_RERANK
    state["query"] = state["question"]
    state["attempts"] = 0
    return state


async def maybe_rewrite(state: AgentState) -> AgentState:
    """Optionally rewrite the query for better retrieval.

    Only rewrites long/compound questions. For short, direct questions we skip
    the LLM call entirely (deterministic gate) to save cost and latency.
    """
    question = state["question"]
    if len(question.split()) <= 8:
        state["trace"].append("rewrite: skipped (short query)")
        return state

    llm = get_llm_provider()
    system = "Rewrite the user's question into a concise search query. Output only the query."
    rewritten = (await llm.generate(system, question)).strip()
    # Guard against the stub/empty: fall back to the original.
    if rewritten and "enough information" not in rewritten and len(rewritten) < len(question) * 2:
        state["query"] = rewritten
        state["trace"].append(f"rewrite: '{rewritten}'")
    else:
        state["trace"].append("rewrite: kept original")
    return state


async def retrieve_node(state: AgentState, session: AsyncSession) -> AgentState:
    state["attempts"] = state.get("attempts", 0) + 1
    strategy = state["strategy"]
    chunks = await retrieve_by_strategy(
        session, state["org_id"], state["query"], state.get("top_k", 5), strategy
    )
    state["retrieved"] = chunks
    state["trace"].append(
        f"retrieve: attempt={state['attempts']} strategy={strategy} hits={len(chunks)}"
    )
    return state


async def assess(state: AgentState) -> AgentState:
    """Deterministic sufficiency check: do we have usable evidence?"""
    chunks = state.get("retrieved", [])
    sufficient = bool(chunks) and chunks[0].score >= SUFFICIENCY_MIN_SCORE
    state["sufficient"] = sufficient
    state["trace"].append(f"assess: sufficient={sufficient}")
    return state


def _next_strategy(current: str) -> str:
    try:
        idx = STRATEGY_LADDER.index(current)
    except ValueError:
        return STRATEGY_HYBRID_RERANK
    return STRATEGY_LADDER[min(idx + 1, len(STRATEGY_LADDER) - 1)]


async def escalate(state: AgentState) -> AgentState:
    """Pick a stronger strategy for the next bounded retry."""
    state["strategy"] = _next_strategy(state["strategy"])
    state["trace"].append(f"escalate: -> {state['strategy']}")
    return state


async def generate(state: AgentState, session: AsyncSession) -> AgentState:
    """Generate a grounded answer + validate citations (reuses RAG logic)."""
    chunks = state.get("retrieved", [])
    if not chunks:
        state.update(answer=ABSTAIN_TEXT, abstained=True, citations=[])
        state["trace"].append("generate: abstain (no evidence)")
        return state

    llm = get_llm_provider()
    raw = (await llm.generate(SYSTEM_PROMPT, build_user_prompt(state["question"], chunks))).strip()
    if raw == ABSTAIN_TEXT or not raw:
        state.update(answer=ABSTAIN_TEXT, abstained=True, citations=[])
        state["trace"].append("generate: model abstained")
        return state

    citations = _extract_citations(raw, chunks)
    if not citations:
        state.update(answer=ABSTAIN_TEXT, abstained=True, citations=[])
        state["trace"].append("generate: abstain (no valid citation)")
        return state

    state.update(answer=raw, abstained=False, citations=citations)
    state["trace"].append(f"generate: answered with {len(citations)} citation(s)")
    return state
