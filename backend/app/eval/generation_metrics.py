"""Generation-quality metrics for RAG answers.

Honest scope: these are heuristic, lexical-overlap proxies -- NOT an
LLM-as-judge presented as ground truth. They are useful as cheap, reproducible
regression signals. For rigorous faithfulness scoring you would add a human or
model judge and treat its output as a noisy estimate, which is a documented
Milestone-6 limitation.

- citation_precision: fraction of answer citations that point to a chunk whose
  text actually supports the cited sentence (lexical-overlap proxy).
- groundedness: fraction of answer tokens that appear in the retrieved context
  (a low value flags possible hallucination / outside knowledge).
- abstention_correct: did the system abstain exactly when it should have?
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def groundedness(answer: str, context_texts: list[str]) -> float:
    """Fraction of answer content-tokens present in the retrieved context."""
    answer_tokens = _tokens(answer)
    if not answer_tokens:
        return 0.0
    context_tokens: set[str] = set()
    for t in context_texts:
        context_tokens |= _tokens(t)
    grounded = answer_tokens & context_tokens
    return len(grounded) / len(answer_tokens)


def citation_precision(cited_texts: list[str], answer: str) -> float:
    """Proxy: fraction of cited chunks that share meaningful overlap with answer."""
    if not cited_texts:
        return 0.0
    answer_tokens = _tokens(answer)
    hits = 0
    for text in cited_texts:
        if len(_tokens(text) & answer_tokens) >= 2:
            hits += 1
    return hits / len(cited_texts)


def abstention_correct(abstained: bool, should_abstain: bool) -> bool:
    return abstained == should_abstain
