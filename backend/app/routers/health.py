"""Health + readiness endpoints.

- /health  : liveness. Is the process up and serving? Always cheap.
- /ready   : readiness. Are downstream dependencies (DB, providers) usable?
             In Milestone 1 there are no dependencies yet, so it mirrors
             /health. We add real dependency checks in later milestones.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_env: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Liveness probe."""
    settings = request.app.state.settings
    return HealthResponse(status="ok", app_env=settings.app_env.value, version="0.1.0")


@router.get("/ready", response_model=HealthResponse)
async def ready(request: Request) -> HealthResponse:
    """Readiness probe (no external deps yet in Milestone 1)."""
    settings = request.app.state.settings
    return HealthResponse(status="ready", app_env=settings.app_env.value, version="0.1.0")
