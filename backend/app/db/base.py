"""SQLAlchemy declarative base + shared column helpers."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def uuid_pk() -> Mapped[uuid.UUID]:
    """A UUID primary key with a server-side default."""
    return mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds created_at / updated_at columns maintained by the DB."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
