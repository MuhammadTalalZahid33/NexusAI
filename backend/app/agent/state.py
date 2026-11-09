"""State for the agentic retrieval workflow.

A single TypedDict flows through the graph; each node reads and updates it.
Keeping all state explicit (not hidden in closures) makes the workflow easy to
trace, log, and test deterministically.
"""

from __future__ import annotations

import uuid
from typing import TypedDict

from app.retrieval.retriever import RetrievedChunk


class AgentState(TypedDict, total=False):
    # Inputs
    org_id: uuid.UUID
    question: str
    top_k: int

    # Working state
    query: str  # possibly rewritten question used for retrieval
    strategy: str  # current retrieval strategy
    attempts: int  # number of retrieval attempts so far (bounded)
    retrieved: list[RetrievedChunk]
    sufficient: bool

    # Trace of decisions for observability.
    trace: list[str]

    # Outputs
    answer: str
    abstained: bool
    citations: list  # list[Citation]
