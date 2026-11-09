"""Chat / question-answering endpoint (baseline RAG)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.documents.deps import get_current_org_id
from app.retrieval.rag import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    strategy: str = Field(
        default="hybrid_rerank",
        pattern="^(vector|hybrid|hybrid_rerank)$",
        description="Retrieval strategy: vector | hybrid | hybrid_rerank",
    )


class CitationOut(BaseModel):
    marker: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    text: str


class AskResponse(BaseModel):
    answer: str
    abstained: bool
    citations: list[CitationOut]


@router.post("", response_model=AskResponse)
async def ask(
    body: AskRequest,
    session: AsyncSession = Depends(get_session),
) -> AskResponse:
    org_id = await get_current_org_id(session)
    result = await answer_question(
        session, org_id, body.question, top_k=body.top_k, strategy=body.strategy
    )
    return AskResponse(
        answer=result.answer,
        abstained=result.abstained,
        citations=[
            CitationOut(
                marker=c.marker,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                page_number=c.page_number,
                text=c.text,
            )
            for c in result.citations
        ],
    )
