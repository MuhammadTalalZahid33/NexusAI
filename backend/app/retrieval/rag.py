"""Baseline RAG pipeline: retrieve -> generate -> validate citations.

Returns a grounded answer plus the citations that back it. If retrieval finds
nothing, or the model abstains, or no valid citation is produced, we return an
honest "insufficient evidence" result instead of a hallucinated answer.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.factory import get_llm_provider
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.prompts import SYSTEM_PROMPT, build_user_prompt
from app.retrieval.retriever import RetrievedChunk, retrieve

ABSTAIN_TEXT = "I don't have enough information to answer that."

# Retrieval strategies, selectable per request + used by the eval harness.
STRATEGY_VECTOR = "vector"
STRATEGY_HYBRID = "hybrid"
STRATEGY_HYBRID_RERANK = "hybrid_rerank"
_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class Citation:
    marker: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    text: str


@dataclass
class RagResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    abstained: bool = False
    retrieved: list[RetrievedChunk] = field(default_factory=list)


async def retrieve_by_strategy(
    session: AsyncSession,
    org_id: uuid.UUID,
    question: str,
    top_k: int,
    strategy: str,
) -> list[RetrievedChunk]:
    """Dispatch to the selected retrieval strategy."""
    if strategy == STRATEGY_VECTOR:
        return await retrieve(session, org_id, question, top_k=top_k)
    if strategy == STRATEGY_HYBRID:
        return await hybrid_retrieve(session, org_id, question, top_k=top_k, use_rerank=False)
    if strategy == STRATEGY_HYBRID_RERANK:
        return await hybrid_retrieve(session, org_id, question, top_k=top_k, use_rerank=True)
    raise ValueError(f"Unknown retrieval strategy: {strategy}")


async def answer_question(
    session: AsyncSession,
    org_id: uuid.UUID,
    question: str,
    top_k: int = 5,
    strategy: str = STRATEGY_HYBRID_RERANK,
) -> RagResult:
    chunks = await retrieve_by_strategy(session, org_id, question, top_k, strategy)

    # No evidence at all -> abstain immediately.
    if not chunks:
        return RagResult(answer=ABSTAIN_TEXT, abstained=True, retrieved=[])

    system = SYSTEM_PROMPT
    user = build_user_prompt(question, chunks)
    llm = get_llm_provider()
    raw_answer = (await llm.generate(system, user)).strip()

    # Model explicitly abstained.
    if raw_answer == ABSTAIN_TEXT or not raw_answer:
        return RagResult(answer=ABSTAIN_TEXT, abstained=True, retrieved=chunks)

    citations = _extract_citations(raw_answer, chunks)

    # Grounding guard: an answer with no valid citation is not trustworthy.
    if not citations:
        return RagResult(answer=ABSTAIN_TEXT, abstained=True, retrieved=chunks)

    return RagResult(answer=raw_answer, citations=citations, retrieved=chunks)


def _extract_citations(answer: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    """Map [n] markers in the answer back to retrieved chunks.

    Only markers that reference a real retrieved source count. This rejects
    fabricated citations (e.g. the model writes [9] when only 5 sources exist).
    """
    seen: set[int] = set()
    citations: list[Citation] = []
    for match in _CITATION_RE.finditer(answer):
        n = int(match.group(1))
        if 1 <= n <= len(chunks) and n not in seen:
            seen.add(n)
            c = chunks[n - 1]
            citations.append(
                Citation(
                    marker=n,
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    filename=c.filename,
                    page_number=c.page_number,
                    text=c.text,
                )
            )
    return citations
