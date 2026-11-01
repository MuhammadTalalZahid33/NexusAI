"""Application configuration.

Settings are loaded from environment variables (and a local `.env` file in
development) and validated by Pydantic at startup. Missing or malformed
required values cause a loud, immediate failure instead of a silent
mis-configuration at runtime -- this is deliberate.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    development = "development"
    production = "production"
    test = "test"


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class Settings(BaseSettings):
    """Typed, validated application settings.

    Values are read from the process environment. In development a `.env`
    file at the backend root is also read (see `model_config`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = AppEnv.development
    log_level: LogLevel = LogLevel.info

    # Comma-separated in the environment, parsed into a list here.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Not required in Milestone 1. Becomes required once persistence lands (M2).
    database_url: str | None = None

    # AI providers -- introduced in later milestones; optional for now.
    gemini_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    cohere_api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be given as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnv.production


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Caching ensures the environment is parsed once per process. Tests can
    clear the cache via `get_settings.cache_clear()` when they need to
    re-read a patched environment.
    """
    return Settings()
