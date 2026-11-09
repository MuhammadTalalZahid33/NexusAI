"""File storage abstraction.

For the MVP we store uploaded files on local disk under a per-org path. This
sits behind a small interface so a cloud object store (S3/GCS) can replace it
later without touching ingestion logic -- same swappability principle as the
AI providers.
"""

from __future__ import annotations

import uuid
from pathlib import Path

# Local storage root (git-ignored). Overridable later via settings/env.
_STORAGE_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


def save_file(org_id: uuid.UUID, document_id: uuid.UUID, data: bytes) -> str:
    """Persist bytes and return a storage key (relative path)."""
    org_dir = _STORAGE_ROOT / str(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    path = org_dir / str(document_id)
    path.write_bytes(data)
    return str(path.relative_to(_STORAGE_ROOT))


def read_file(key: str) -> bytes:
    return (_STORAGE_ROOT / key).read_bytes()


def delete_file(key: str) -> None:
    path = _STORAGE_ROOT / key
    if path.exists():
        path.unlink()
