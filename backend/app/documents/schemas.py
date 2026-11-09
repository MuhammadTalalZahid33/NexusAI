"""API schemas for document endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    error: str | None
    page_count: int | None
    chunk_count: int
    created_at: datetime


class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
