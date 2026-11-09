"""Authentication dependencies.

`get_current_principal` extracts and verifies the JWT, returning the
authenticated principal (user id, org id, role). Every protected endpoint
depends on this, and every data query scopes by `principal.org_id`. This is the
tenant-isolation boundary -- enforced server-side, never trusting the client.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.db.models import UserRole

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: UserRole


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired.") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token.") from exc

    try:
        return Principal(
            user_id=uuid.UUID(payload["sub"]),
            org_id=uuid.UUID(payload["org"]),
            role=UserRole(payload["role"]),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token.") from exc


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role is not UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required.")
    return principal
