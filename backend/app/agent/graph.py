"""Agentic retrieval graph (LangGraph).

Flow:
    classify -> maybe_rewrite -> retrieve -> assess
                                               |
                         sufficient? -----no---+--> (attempts < MAX) escalate -> retrieve
                               |                     (attempts >= MAX) -------> generate
                              yes -> generate -> END

The loop is bounded by MAX_ATTEMPTS: on insufficient evidence we escalate the
strategy and retry at most MAX_ATTEMPTS times, then generate (which will abstain
honestly if evidence is still weak). No path can loop indefinitely.
"""

from __future__ import annotations

import uuid
from functools import partial

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import nodes
from app.agent.state import AgentState
from app.retrieval.rag import Citation, RagResult


def _route_after_assess(state: AgentState) -> str:
    """Conditional edge: decide whether to generate, escalate+retry, or give up."""
    if state.get("sufficient"):
        return "generate"
    if state.get("attempts", 0) < nodes.MAX_ATTEMPTS:
        return "escalate"
    return "generate"  # exhausted retries -> generate (will abstain if weak)


def build_graph(session: AsyncSession):
    """Compile the workflow graph bound to a DB session."""
    graph = StateGraph(AgentState)

    graph.add_node("classify", nodes.classify)
    graph.add_node("maybe_rewrite", nodes.maybe_rewrite)
    graph.add_node("retrieve", partial(nodes.retrieve_node, session=session))
    graph.add_node("assess", nodes.assess)
    graph.add_node("escalate", nodes.escalate)
    graph.add_node("generate", partial(nodes.generate, session=session))

    graph.set_entry_point("classify")
    graph.add_edge("classify", "maybe_rewrite")
    graph.add_edge("maybe_rewrite", "retrieve")
    graph.add_edge("retrieve", "assess")
    graph.add_conditional_edges(
        "assess",
        _route_after_assess,
        {"generate": "generate", "escalate": "escalate"},
    )
    graph.add_edge("escalate", "retrieve")
    graph.add_edge("generate", END)

    return graph.compile()


async def run_agent(
    session: AsyncSession,
    org_id: uuid.UUID,
    question: str,
    top_k: int = 5,
) -> RagResult:
    """Public entrypoint: run the agentic workflow and return a RagResult."""
    app = build_graph(session)
    initial: AgentState = {"org_id": org_id, "question": question, "top_k": top_k}
    final: AgentState = await app.ainvoke(initial)

    citations: list[Citation] = final.get("citations", []) or []
    return RagResult(
        answer=final.get("answer", ""),
        citations=citations,
        abstained=final.get("abstained", True),
        retrieved=final.get("retrieved", []) or [],
    )
