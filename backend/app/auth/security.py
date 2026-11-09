"""Password hashing + JWT issuance/verification.

- Passwords are hashed with bcrypt (via passlib). Never stored or logged raw.
- Access tokens are signed JWTs carrying the user id, org id, and role. The org
  id in the token is the tenant boundary used by every downstream query.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings


def _prepare(password: str) -> bytes:
    """Encode + enforce bcrypt's 72-byte input limit.

    bcrypt only considers the first 72 bytes. Newer bcrypt raises instead of
    silently truncating, so we truncate explicitly and deterministically. For
    very long passphrases this is standard practice (or pre-hash with sha256).
    """
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
