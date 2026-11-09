"""Chunking: split extracted page text into overlapping, token-sized pieces.

Why token-aware (not character count)?
  Embedding models have token limits and "think" in tokens. Sizing chunks by
  tokens keeps each chunk safely within model limits and makes chunk size
  comparable across documents regardless of word length.

Strategy (baseline):
  Recursive split -- try to break on the largest natural boundary that fits
  (paragraph -> line -> sentence -> word), so chunks end at sensible places
  instead of mid-word. Consecutive chunks share `overlap` tokens so a fact
  spanning a boundary isn't lost to both sides.

Each chunk keeps the page_number of the page it came from -> citations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from app.documents.extraction import PageText

# A stable, model-agnostic tokenizer for *sizing*. We are not calling an LLM
# here -- we just need a consistent token count. cl100k_base is widely used.
_ENCODER = tiktoken.get_encoding("cl100k_base")

# Boundaries to try, largest first.
_SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass
class Chunk:
    chunk_index: int
    page_number: int | None
    text: str
    token_count: int


def count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


def chunk_pages(
    pages: list[PageText],
    *,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> list[Chunk]:
    """Chunk every page, numbering chunks sequentially across the document."""
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")

    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        for text in _split_text(page.text, chunk_size_tokens, chunk_overlap_tokens):
            chunks.append(
                Chunk(
                    chunk_index=index,
                    page_number=page.page_number,
                    text=text,
                    token_count=count_tokens(text),
                )
            )
            index += 1
    return chunks


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split one page's text into token-bounded, overlapping windows."""
    text = text.strip()
    if not text:
        return []

    # Break into atomic pieces on natural boundaries first.
    pieces = _recursive_split(text, size)

    # Greedily pack pieces into windows up to `size` tokens, then slide back
    # by `overlap` tokens to start the next window.
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for piece in pieces:
        piece_tokens = count_tokens(piece)
        if current_tokens + piece_tokens > size and current:
            chunks.append(" ".join(current).strip())
            # Build overlap tail from the end of the current window.
            current, current_tokens = _overlap_tail(current, overlap)
        current.append(piece)
        current_tokens += piece_tokens

    if current:
        chunks.append(" ".join(current).strip())

    return [c for c in chunks if c]


def _recursive_split(text: str, size: int) -> list[str]:
    """Split text into pieces each <= size tokens, trying natural boundaries."""
    if count_tokens(text) <= size:
        return [text]

    for sep in _SEPARATORS:
        if sep in text:
            parts = _resplit_keep(text, sep)
            result: list[str] = []
            for part in parts:
                if count_tokens(part) <= size:
                    result.append(part)
                else:
                    result.extend(_recursive_split(part, size))
            return [p for p in result if p.strip()]

    # No separator worked (e.g. one huge token run): hard-split by tokens.
    return _hard_split_by_tokens(text, size)


def _resplit_keep(text: str, sep: str) -> list[str]:
    """Split on sep but keep sentence-ending punctuation attached."""
    if sep == ". ":
        parts = re.split(r"(?<=\.)\s+", text)
    else:
        parts = text.split(sep)
    return [p for p in parts if p.strip()]


def _hard_split_by_tokens(text: str, size: int) -> list[str]:
    tokens = _ENCODER.encode(text)
    return [_ENCODER.decode(tokens[i : i + size]) for i in range(0, len(tokens), size)]


def _overlap_tail(pieces: list[str], overlap: int) -> tuple[list[str], int]:
    """Return the trailing pieces whose combined tokens ~= overlap."""
    if overlap <= 0:
        return [], 0
    tail: list[str] = []
    total = 0
    for piece in reversed(pieces):
        t = count_tokens(piece)
        if total + t > overlap and tail:
            break
        tail.insert(0, piece)
        total += t
    return tail, total
