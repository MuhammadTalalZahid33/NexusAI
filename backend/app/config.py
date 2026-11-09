"""Application configuration.

Settings are loaded from environment variables (and a local `.env` file in
development) and validated by Pydantic at startup. Missing or malformed
required values cause a loud, immediate failure instead of a silent
mis-configuration at runtime -- this is deliberate.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the repo-root .env regardless of the current working directory.
# config.py lives at backend/app/config.py -> parents[2] is the repo root.
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


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
        # Read both the repo-root .env and a backend-local .env if present.
        # Later entries win, so a backend/.env can override the root for local tweaks.
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_env: AppEnv = AppEnv.development
    log_level: LogLevel = LogLevel.info

    # Stored as a raw comma-separated string to avoid pydantic-settings trying
    # to JSON-decode a list field from the .env. Use `cors_origins` (property).
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="cors_origins")

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins, parsed from a comma-separated string."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    # Required from Milestone 2 on. A Neon/Postgres connection string.
    database_url: str | None = None

    @property
    def async_database_url(self) -> str:
        """Return the DATABASE_URL normalized to the asyncpg driver.

        Neon/most providers hand out a `postgresql://...` URL. SQLAlchemy's
        async engine needs the `postgresql+asyncpg://` scheme. We also drop a
        `sslmode=require` query param if present, because asyncpg does not
        accept it as a URL arg (SSL is handled via connect_args instead).
        """
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured.")
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        # Strip sslmode (asyncpg uses connect_args for SSL, not the URL).
        for sep in ("?sslmode=require", "&sslmode=require"):
            url = url.replace(sep, "")
        return url

    # AI providers -- introduced in later milestones; optional for now.
    gemini_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    cohere_api_key: str | None = None

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
