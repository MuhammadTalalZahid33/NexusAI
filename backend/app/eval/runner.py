"""Evaluation runner.

Loads the seed dataset, ingests its documents into a temporary eval org,
runs retrieval for each question, and reports retrieval metrics. Results are
written to eval/reports/ so improvements across milestones are comparable.

Ground truth is at the *document* level (which document should the top chunk
come from) plus a substring check (did we retrieve the specific passage).
This is honest about its limitations: a small synthetic set, binary relevance,
no LLM-as-judge claimed as truth.

Run:  python -m app.eval.runner
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete

from app.db.models import Chunk, Document, DocumentStatus, Organization
from app.db.session import get_sessionmaker
from app.documents.chunking import chunk_pages
from app.documents.extraction import PageText
from app.eval.metrics import aggregate
from app.providers.factory import get_embedding_provider
from app.retrieval.retriever import retrieve

_ROOT = Path(__file__).resolve().parents[3]
_DATASET = _ROOT / "eval" / "dataset.json"
_REPORTS = _ROOT / "eval" / "reports"
_EVAL_ORG = "__EVAL_ORG__"
TOP_K = 5


async def _reset_eval_org(session) -> uuid.UUID:
    org = await session.scalar(
        __import__("sqlalchemy").select(Organization).where(Organization.name == _EVAL_ORG)
    )
    if org is not None:
        await session.execute(delete(Chunk).where(Chunk.org_id == org.id))
        await session.execute(delete(Document).where(Document.org_id == org.id))
        await session.execute(delete(Organization).where(Organization.id == org.id))
        await session.commit()
    org = Organization(name=_EVAL_ORG)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org.id


async def _ingest(session, org_id: uuid.UUID, dataset: dict) -> dict[uuid.UUID, str]:
    """Ingest each eval document; return chunk_id -> source doc id map."""
    emb = get_embedding_provider()
    chunk_to_doc: dict[uuid.UUID, str] = {}
    for d in dataset["documents"]:
        doc = Document(
            org_id=org_id,
            filename=d["filename"],
            mime_type="text/plain",
            size_bytes=len(d["text"]),
            status=DocumentStatus.ready,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        chunks = chunk_pages(
            [PageText(page_number=1, text=d["text"])],
            chunk_size_tokens=120,
            chunk_overlap_tokens=20,
        )
        vecs = await emb.embed_documents([c.text for c in chunks])
        for c, v in zip(chunks, vecs, strict=True):
            row = Chunk(
                document_id=doc.id,
                org_id=org_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                text=c.text,
                token_count=c.token_count,
                embedding=v,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            chunk_to_doc[row.id] = d["id"]
    return chunk_to_doc


async def run() -> dict:
    dataset = json.loads(_DATASET.read_text(encoding="utf-8"))
    maker = get_sessionmaker()
    async with maker() as session:
        org_id = await _reset_eval_org(session)
        chunk_to_doc = await _ingest(session, org_id, dataset)

        per_retrieved: list[list[str]] = []
        per_relevant: list[set[str]] = []
        substring_hits = 0

        for q in dataset["questions"]:
            results = await retrieve(session, org_id, q["question"], top_k=TOP_K)
            # Map each retrieved chunk to its source document id, then dedupe to
            # first occurrence so ranking is at the document level (a document's
            # rank = position of its first retrieved chunk). Without dedup,
            # multiple chunks of one doc would inflate DCG above the ideal.
            seen: set[str] = set()
            retrieved_docs: list[str] = []
            for r in results:
                d = chunk_to_doc.get(r.chunk_id, "?")
                if d not in seen:
                    seen.add(d)
                    retrieved_docs.append(d)
            per_retrieved.append(retrieved_docs)
            per_relevant.append({q["relevant_doc"]})
            # Substring check: did any retrieved chunk contain the gold passage?
            if any(q["relevant_substring"] in r.text for r in results):
                substring_hits += 1

        metrics = aggregate(per_retrieved, per_relevant, k=TOP_K)
        metrics["passage_hit_rate"] = substring_hits / len(dataset["questions"])

        # cleanup
        await session.execute(delete(Chunk).where(Chunk.org_id == org_id))
        await session.execute(delete(Document).where(Document.org_id == org_id))
        await session.execute(delete(Organization).where(Organization.id == org_id))
        await session.commit()

    emb_impl = type(get_embedding_provider()).__name__
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "embedding_provider": emb_impl,
        "top_k": TOP_K,
        "num_questions": len(dataset["questions"]),
        "metrics": metrics,
    }
    _REPORTS.mkdir(parents=True, exist_ok=True)
    out = _REPORTS / f"baseline_{emb_impl}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = asyncio.run(run())
    print(json.dumps(result, indent=2))
