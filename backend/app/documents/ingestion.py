"""Document ingestion pipeline (runs in the background).

Flow: load file -> extract pages -> chunk -> store chunks -> mark ready.
Any failure marks the document `failed` with the error message, so the user
sees a clear status instead of a silent hang.

Embeddings are intentionally NOT produced here yet -- that is Milestone 3.
Chunks are stored with embedding=NULL for now.

This function is scheduled via FastAPI BackgroundTasks for the MVP. It is kept
as a plain async function taking a sessionmaker so that swapping to a Redis/ARQ
worker later means calling the same function from a different place.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Chunk, Document, DocumentStatus
from app.documents import storage
from app.documents.chunking import chunk_pages
from app.documents.extraction import ExtractionError, extract_pages
from app.logging_config import get_logger
from app.providers.factory import get_embedding_provider

log = get_logger(__name__)

# Embed in batches to respect provider rate/size limits.
_EMBED_BATCH_SIZE = 64


async def ingest_document(
    sessionmaker: async_sessionmaker,
    document_id: uuid.UUID,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> None:
    """Process one document end-to-end. Safe to call in the background."""
    async with sessionmaker() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            log.warning("ingest.document_missing", document_id=str(document_id))
            return

        doc.status = DocumentStatus.processing
        await session.commit()

        try:
            data = storage.read_file(doc.storage_key) if doc.storage_key else b""
            pages = extract_pages(data, doc.mime_type, doc.filename)
            chunks = chunk_pages(
                pages,
                chunk_size_tokens=chunk_size_tokens,
                chunk_overlap_tokens=chunk_overlap_tokens,
            )

            # Clear any prior chunks (idempotent re-runs / retries).
            existing = await session.scalars(
                select(Chunk).where(Chunk.document_id == doc.id)
            )
            for c in existing:
                await session.delete(c)

            # Embed chunk texts in batches (respects provider limits).
            embeddings = await _embed_all([c.text for c in chunks])

            for ch, emb in zip(chunks, embeddings, strict=True):
                session.add(
                    Chunk(
                        document_id=doc.id,
                        org_id=doc.org_id,
                        chunk_index=ch.chunk_index,
                        page_number=ch.page_number,
                        text=ch.text,
                        token_count=ch.token_count,
                        embedding=emb,
                    )
                )

            doc.page_count = max((p.page_number or 0) for p in pages) or None
            doc.chunk_count = len(chunks)
            doc.status = DocumentStatus.ready
            doc.error = None
            await session.commit()
            log.info(
                "ingest.ready",
                document_id=str(doc.id),
                chunks=len(chunks),
                pages=doc.page_count,
            )
        except ExtractionError as exc:
            await _mark_failed(session, doc, str(exc))
            log.warning("ingest.failed", document_id=str(doc.id), reason=str(exc))
        except Exception as exc:  # unexpected -> still fail cleanly
            await _mark_failed(session, doc, f"Unexpected error: {exc}")
            log.exception("ingest.error", document_id=str(doc.id))


async def _embed_all(texts: list[str]) -> list[list[float]]:
    """Embed all chunk texts in batches via the active embedding provider."""
    provider = get_embedding_provider()
    out: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        out.extend(await provider.embed_documents(batch))
    return out


async def _mark_failed(session, doc: Document, message: str) -> None:
    doc.status = DocumentStatus.failed
    doc.error = message[:2000]
    await session.commit()
