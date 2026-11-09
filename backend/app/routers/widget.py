"""Embeddable widget API.

Two audiences (per the product requirement):
- Admins manage API keys for their org (create/list/revoke).
- The widget calls /widget/ask with an `X-API-Key` header. The key resolves to
  exactly one org server-side, so tenant isolation holds for anonymous traffic.

Public-scope keys allow read-only Q&A over the org's documents. The raw key is
shown ONCE at creation; only its hash is stored.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import Principal, require_admin
from app.db.models import ApiKey, ApiKeyScope
from app.db.session import get_session
from app.observability.metrics import REGISTRY, track_latency
from app.retrieval.rag import answer_question

router = APIRouter(prefix="/widget", tags=["widget"])


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scope: ApiKeyScope = ApiKeyScope.public


class CreateKeyResponse(BaseModel):
    id: str
    name: str
    scope: ApiKeyScope
    api_key: str  # shown once


class KeyOut(BaseModel):
    id: str
    name: str
    scope: ApiKeyScope
    active: bool


class WidgetAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class WidgetAskResponse(BaseModel):
    answer: str
    abstained: bool
    citations: list[dict]


@router.post("/keys", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: CreateKeyRequest,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> CreateKeyResponse:
    raw = f"nxs_{secrets.token_urlsafe(32)}"
    key = ApiKey(
        org_id=principal.org_id,
        name=body.name,
        key_hash=_hash_key(raw),
        scope=body.scope,
    )
    session.add(key)
    await session.commit()
    await session.refresh(key)
    return CreateKeyResponse(id=str(key.id), name=key.name, scope=key.scope, api_key=raw)


@router.get("/keys", response_model=list[KeyOut])
async def list_keys(
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[KeyOut]:
    keys = await session.scalars(select(ApiKey).where(ApiKey.org_id == principal.org_id))
    return [KeyOut(id=str(k.id), name=k.name, scope=k.scope, active=k.active) for k in keys]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: str,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    key = await session.get(ApiKey, key_id)
    if key is None or key.org_id != principal.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not found.")
    key.active = False
    await session.commit()


async def _resolve_api_key(session: AsyncSession, raw_key: str) -> ApiKey:
    key = await session.scalar(
        select(ApiKey).where(ApiKey.key_hash == _hash_key(raw_key), ApiKey.active.is_(True))
    )
    if key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive API key.")
    return key


@router.post("/ask", response_model=WidgetAskResponse)
async def widget_ask(
    body: WidgetAskRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> WidgetAskResponse:
    """Anonymous/widget Q&A. The API key resolves to exactly one org."""
    key = await _resolve_api_key(session, x_api_key)
    REGISTRY.incr("widget.requests")
    with track_latency("widget.answer"):
        result = await answer_question(
            session, key.org_id, body.question, top_k=body.top_k, strategy="hybrid_rerank"
        )
    return WidgetAskResponse(
        answer=result.answer,
        abstained=result.abstained,
        citations=[
            {
                "marker": c.marker,
                "filename": c.filename,
                "page_number": c.page_number,
                "text": c.text,
            }
            for c in result.citations
        ],
    )
