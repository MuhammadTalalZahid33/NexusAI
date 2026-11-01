"""Tests for configuration loading + validation."""

from __future__ import annotations

from app.config import AppEnv, Settings


def test_defaults() -> None:
    settings = Settings(app_env=AppEnv.test)
    assert settings.app_env is AppEnv.test
    assert settings.llm_model  # has a sensible default
    assert settings.is_production is False


def test_cors_origins_parsed_from_comma_string() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_production_flag() -> None:
    settings = Settings(app_env=AppEnv.production)
    assert settings.is_production is True
