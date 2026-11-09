"""FastAPI application entrypoint.

Wires together configuration, logging, CORS, request-scoped logging, and
the API routers. Keeping this file thin makes the app easy to reason about
and to test (we build the app via a factory so tests get a fresh instance).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.logging_config import configure_logging, get_logger
from app.routers import auth, chat, documents, health, metrics, widget

log = get_logger(__name__)

# Shared limiter keyed by client IP. Per-route limits are applied in routers
# via `@limiter.limit(...)`. This protects uploads and widget traffic from abuse.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks. Later milestones open DB pools here."""
    settings: Settings = app.state.settings
    log.info("app.startup", app_env=settings.app_env.value, log_level=settings.log_level.value)
    yield
    log.info("app.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Accepting an optional Settings object lets tests inject a custom
    configuration without touching the real environment.
    """
    settings = settings or get_settings()
    configure_logging(settings.app_env, settings.log_level)

    app = FastAPI(
        title="Nexus AI",
        version="0.1.0",
        description="Agentic RAG knowledge intelligence platform.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind a request id + log each request with latency."""
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception("request.error", duration_ms=duration_ms)
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info("request.complete", status_code=response.status_code, duration_ms=duration_ms)
        response.headers["x-request-id"] = request_id
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    app.include_router(widget.router)
    app.include_router(metrics.router)
    return app


app = create_app()
