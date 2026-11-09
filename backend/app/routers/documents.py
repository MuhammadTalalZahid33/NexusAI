"""Document endpoints: upload, list, status, delete.

Tenant isolation: every query filters by the current org_id. A document that
belongs to another org returns 404 (not 403) so we don't leak existence.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import Document, DocumentStatus
from app.db.session import get_session, get_sessionmaker
from app.documents import storage
from app.documents.deps import get_current_org_id
from app.documents.ingestion import ingest_document
from app.documents.schemas import DocumentListOut, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_ALLOWED_EXT = (".pdf", ".docx")


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DocumentOut:
    filename = file.filename or "upload"
    content_type = file.content_type or ""

    # Validate type (by content-type OR extension; browsers vary).
    if content_type not in _ALLOWED and not filename.lower().endswith(_ALLOWED_EXT):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.",
        )

    org_id = await get_current_org_id(session)

    doc = Document(
        org_id=org_id,
        filename=filename,
        mime_type=content_type or "application/octet-stream",
        size_bytes=len(data),
        status=DocumentStatus.pending,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    doc.storage_key = storage.save_file(org_id, doc.id, data)
    await session.commit()
    await session.refresh(doc)

    # Schedule async ingestion. Uses its own session/sessionmaker so it does
    # not depend on this request's session lifetime.
    background.add_task(
        ingest_document,
        get_sessionmaker(),
        doc.id,
        settings.chunk_size_tokens,
        settings.chunk_overlap_tokens,
    )

    return DocumentOut.model_validate(doc)


@router.get("", response_model=DocumentListOut)
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> DocumentListOut:
    org_id = await get_current_org_id(session)
    docs = await session.scalars(
        select(Document).where(Document.org_id == org_id).order_by(Document.created_at.desc())
    )
    return DocumentListOut(documents=[DocumentOut.model_validate(d) for d in docs])


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    org_id = await get_current_org_id(session)
    doc = await _get_owned(session, document_id, org_id)
    return DocumentOut.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = await get_current_org_id(session)
    doc = await _get_owned(session, document_id, org_id)
    if doc.storage_key:
        storage.delete_file(doc.storage_key)
    # Chunks cascade-delete via the FK relationship.
    await session.delete(doc)
    await session.commit()


async def _get_owned(session: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID) -> Document:
    doc = await session.get(Document, document_id)
    if doc is None or doc.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc
