"""Operational metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.observability.metrics import REGISTRY

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics() -> dict:
    """Return a snapshot of in-process operational metrics."""
    return REGISTRY.snapshot()
