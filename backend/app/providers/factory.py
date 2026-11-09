"""Provider selection.

Chooses concrete providers based on settings. If a Gemini API key is present
we use the real Gemini providers; otherwise we fall back to the deterministic
stub so the whole system runs offline, for free, and in CI.

This is the single place that knows which provider is active. Everything else
depends only on the abstract interfaces in providers/base.py.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.db.models import EMBEDDING_DIM
from app.logging_config import get_logger
from app.providers.base import EmbeddingProvider, LLMProvider, RerankerProvider
from app.providers.stub import (
    StubEmbeddingProvider,
    StubLLMProvider,
    StubRerankerProvider,
)

log = get_logger(__name__)


def _use_gemini(settings: Settings) -> bool:
    return bool(settings.gemini_api_key)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if _use_gemini(settings):
        from app.providers.gemini import GeminiEmbeddingProvider

        log.info("providers.embedding", impl="gemini", model=settings.embedding_model)
        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.embedding_model,
            dim=EMBEDDING_DIM,
        )
    log.info("providers.embedding", impl="stub", dim=EMBEDDING_DIM)
    return StubEmbeddingProvider(dim=EMBEDDING_DIM)


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if _use_gemini(settings):
        from app.providers.gemini import GeminiLLMProvider

        log.info("providers.llm", impl="gemini", model=settings.llm_model)
        return GeminiLLMProvider(api_key=settings.gemini_api_key or "", model=settings.llm_model)
    log.info("providers.llm", impl="stub")
    return StubLLMProvider()


@lru_cache
def get_reranker_provider() -> RerankerProvider:
    settings = get_settings()
    if settings.cohere_api_key:
        from app.providers.cohere import CohereRerankerProvider

        log.info("providers.reranker", impl="cohere")
        return CohereRerankerProvider(api_key=settings.cohere_api_key)
    log.info("providers.reranker", impl="stub")
    return StubRerankerProvider()
