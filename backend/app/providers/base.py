"""Provider interfaces (ports).

All AI inference goes through these abstract interfaces. Concrete providers
(stub, Gemini, OpenAI, Cohere) implement them. This is the swappability
backbone: changing providers is a config change, not a rewrite, and tests can
run against the deterministic stub with no network or API key.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class EmbeddingProvider(ABC):
    """Turns text into dense vectors for semantic search."""

    #: Dimension of the vectors this provider returns.
    dim: int

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts (for ingestion)."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query (for retrieval).

        Kept separate from embed_documents because some models use different
        task-type prompts for queries vs documents.
        """


class LLMProvider(ABC):
    """Generates answers from a prompt."""

    @abstractmethod
    async def generate(self, system: str, user: str) -> str:
        """Return a complete answer."""

    @abstractmethod
    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        """Yield answer tokens/chunks as they are produced."""
