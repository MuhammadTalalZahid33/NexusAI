"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import AppEnv, LogLevel, Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Deterministic settings for tests (no reliance on the real env)."""
    return Settings(
        app_env=AppEnv.test,
        log_level=LogLevel.warning,
        cors_origins=["http://testserver"],
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """A TestClient backed by a freshly-built app with test settings."""
    app = create_app(settings=test_settings)
    return TestClient(app)
