# Evaluation

Retrieval and answer quality are measured with a reproducible harness so that
changes can be compared objectively rather than asserted. This document is
deliberately honest about what the numbers do and do not show.

## How to run

```powershell
cd backend
python -m app.eval.runner      # writes eval/reports/compare_<provider>.json
```

The runner ingests the seed dataset into a temporary org, runs each retrieval
strategy over every question, computes metrics, and cleans up.

## Dataset

`eval/dataset.json` — a small **seed** set: 3 synthetic documents (HR policy,
security policy, product FAQ) and 10 questions. Each question has a known
relevant document and a gold passage substring.

This is intentionally small for the current stage. The roadmap expands it to
100–200 question/evidence pairs (Milestone 6+) for statistically meaningful
numbers. Treat current results as a **plumbing-correct baseline**, not a
benchmark claim.

## Metrics

**Retrieval** (document-level relevance; retrieved chunks are deduped to their
source document so ranking is per-document):
- **Recall@k** — fraction of relevant docs appearing in the top k.
- **MRR** — mean reciprocal rank of the first relevant doc.
- **nDCG@k** — rewards ranking relevant docs higher.
- **passage_hit_rate** — did any retrieved chunk contain the exact gold passage.

**Generation** (`app/eval/generation_metrics.py`, heuristic proxies — **not** an
LLM-as-judge presented as truth):
- **groundedness** — fraction of answer tokens present in retrieved context
  (low ⇒ possible hallucination).
- **citation_precision** — fraction of cited chunks that overlap the answer.
- **abstention_correct** — did the system abstain exactly when it should.

## Baseline results (stub providers)

Run with deterministic **stub** embeddings + reranker (no API keys), top_k=5,
10 questions:

| Strategy        | Recall@5 | MRR   | nDCG@5 | Passage hit |
|-----------------|----------|-------|--------|-------------|
| vector          | 1.00     | 0.933 | 0.950  | 1.00        |
| hybrid          | 1.00     | 0.933 | 0.950  | 1.00        |
| hybrid_rerank   | 1.00     | 0.950 | 0.963  | 1.00        |

**Reading these honestly:**
- The seed set is small and topically distinct, so even crude stub embeddings
  retrieve the right document every time (Recall@5 = 1.0). The set is too easy to
  separate the strategies much.
- `hybrid_rerank` shows a small MRR/nDCG gain (better ordering), which is the
  *direction* we expect; the magnitude is understated because the task is easy
  and the stub reranker is a lexical proxy.
- The meaningful comparison is with **real Gemini embeddings + Cohere rerank** on
  an **expanded dataset** — expected to widen the gap between strategies. That
  run is the honest headline result and is reproduced by setting API keys and
  re-running the same harness.

## Limitations

- Small synthetic dataset; binary relevance; document-level ground truth.
- Stub providers understate real-world quality differences.
- Generation metrics are lexical proxies, not semantic judgments.
- No human evaluation yet. An LLM-as-judge, if added, is a noisy estimate — not
  ground truth.

## What this demonstrates

Even at baseline, the harness proves the capability that matters for an AI
engineering portfolio: **the system can measure retrieval and answer quality
reproducibly, compare strategies on equal footing, and report results honestly
with their limitations** — rather than claiming a feature is "advanced" without
evidence.
