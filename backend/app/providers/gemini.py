"""Gemini provider implementations (real API).

Uses the current `google-genai` client SDK. The package is imported lazily so
the app runs without it (and without a key) when using the stub provider.

Free-tier note: Gemini embedding + generation free tiers are rate-limited
(embeddings especially: ~100 rpm / ~1k per day historically). Ingestion batches
and backs off to stay within limits -- see embed_documents.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.logging_config import get_logger
from app.providers.base import EmbeddingProvider, LLMProvider

log = get_logger(__name__)


def _client(api_key: str):
    try:
        from google import genai  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc
    return genai.Client(api_key=api_key)


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dim: int = 768) -> None:
        self._client = _client(api_key)
        self._model = model
        self.dim = dim

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Embed one batch; callers (ingestion) chunk large sets + handle backoff.
        return await asyncio.to_thread(self._embed_batch, texts, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        result = await asyncio.to_thread(self._embed_batch, [text], "RETRIEVAL_QUERY")
        return result[0]

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types  # type: ignore

        resp = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dim,
            ),
        )
        return [list(e.values) for e in resp.embeddings]


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = _client(api_key)
        self._model = model

    async def generate(self, system: str, user: str) -> str:
        return await asyncio.to_thread(self._generate_sync, system, user)

    def _generate_sync(self, system: str, user: str) -> str:
        from google.genai import types  # type: ignore

        resp = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,  # low temp -> more faithful, less creative
            ),
        )
        return resp.text or ""

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        # The SDK streaming call is sync; bridge it to async by running the
        # generator in a thread and forwarding chunks through a queue.
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def produce() -> None:
            from google.genai import types  # type: ignore

            try:
                stream = self._client.models.generate_content_stream(
                    model=self._model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system, temperature=0.2
                    ),
                )
                for chunk in stream:
                    if chunk.text:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        task = asyncio.create_task(asyncio.to_thread(produce))
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        await task
