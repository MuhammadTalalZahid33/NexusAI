"""Async database engine + session management.

The engine is created once per process. `get_session` is a FastAPI dependency
that yields a session per request and ensures it is closed afterwards.
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create (once) and return the async engine."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = settings or get_settings()
        # Neon requires TLS. asyncpg accepts an ssl.SSLContext (or "require"
        # in recent versions). A default client context works with Neon.
        ssl_context = ssl.create_default_context()
        _engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_pre_ping=True,  # detect dropped connections (Neon scales to zero)
            connect_args={"ssl": ssl_context},
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session, always close it."""
    maker = get_sessionmaker()
    async with maker() as session:
        yield session
