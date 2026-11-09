"""Baseline vector retrieval.

Given a query, embed it and find the nearest chunks by cosine distance using
pgvector, scoped to the caller's organization. Org scoping is enforced in the
SQL WHERE clause -- the tenant boundary, not a frontend concern.

This is deliberately the simplest useful retriever. Hybrid search + reranking
come in Milestone 4 so we can measure their improvement against this baseline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document
from app.providers.factory import get_embedding_provider


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    text: str
    score: float  # higher = more similar (1 - cosine_distance)


async def retrieve(
    session: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Return the top_k most similar chunks for the query within the org."""
    provider = get_embedding_provider()
    query_embedding = await provider.embed_query(query)

    # pgvector cosine distance operator via SQLAlchemy. Smaller distance =
    # more similar; we convert to a similarity score for readability.
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Document.filename,
            Chunk.page_number,
            Chunk.text,
            distance,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.org_id == org_id)
        .where(Chunk.embedding.isnot(None))
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    return [
        RetrievedChunk(
            chunk_id=row.id,
            document_id=row.document_id,
            filename=row.filename,
            page_number=row.page_number,
            text=row.text,
            score=1.0 - float(row.distance),
        )
        for row in rows
    ]


async def keyword_retrieve(
    session: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """Full-text keyword search via Postgres tsvector + ts_rank, org-scoped.

    Complements vector search: great at exact terms, names, numbers, and rare
    jargon that embeddings sometimes blur. Uses websearch_to_tsquery so natural
    queries ("payment terms") work without special syntax.
    """
    tsquery = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank(text("chunks.tsv"), tsquery).label("rank")
    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Document.filename,
            Chunk.page_number,
            Chunk.text,
            rank,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.org_id == org_id)
        .where(text("chunks.tsv @@ websearch_to_tsquery('english', :q)"))
        .order_by(rank.desc())
        .limit(top_k)
    ).params(q=query)
    rows = (await session.execute(stmt)).all()
    return [
        RetrievedChunk(
            chunk_id=row.id,
            document_id=row.document_id,
            filename=row.filename,
            page_number=row.page_number,
            text=row.text,
            score=float(row.rank),
        )
        for row in rows
    ]
