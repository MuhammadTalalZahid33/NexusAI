"""add documents.storage_key

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("storage_key", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "storage_key")
