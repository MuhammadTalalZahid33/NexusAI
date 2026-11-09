# Architecture & Design Decisions

This document explains the system design and the trade-offs behind each major
decision. It is written to be read by an engineer evaluating the project.

## 1. Shape: modular monolith

One FastAPI service, one PostgreSQL database, clear internal module boundaries
(`auth`, `documents`, `retrieval`, `agent`, `eval`, `providers`, `observability`).

**Why not microservices?** At this scale they add operational cost (multiple
deploys, network hops, distributed tracing) without benefit. The module
boundaries give microservice-style separation *in code*; any module could be
extracted later if load demanded it. This is the honest right answer for a
single-team, single-product system, and it is defensible in an interview as
"scalable design without premature infrastructure."

## 2. Provider abstraction (ports & adapters)

`providers/base.py` defines `EmbeddingProvider`, `LLMProvider`, and
`RerankerProvider`. Concrete adapters: deterministic **stubs** (offline, free,
used in tests/CI) and real **Gemini**/**Cohere**. `providers/factory.py` is the
only place that knows which implementation is active, chosen by whether API keys
are configured.

**Why:** swapping a free tier for a paid provider — or Gemini for OpenAI — is a
config change, not a rewrite. Tests never depend on a live API or a key. This
directly supports the "free to build and demo, designed to scale with cost"
constraint.

## 3. Data model & tenant isolation

Tables: `organizations`, `users`, `documents`, `chunks`, `api_keys`.

`org_id` is denormalized onto `chunks` (not just `documents`) so **every
retrieval query filters by `org_id` in a single SQL `WHERE` clause**. Tenant
isolation is a server-side database boundary, never frontend filtering. Cross-org
access returns 404 (not 403) to avoid leaking resource existence. This is
verified by an integration test that creates two orgs and asserts one cannot see
the other's documents.

## 4. Ingestion pipeline (async)

`upload → validate (type/size) → store file → document(pending) → background
task: extract → chunk → embed → store chunks → document(ready|failed)`.

- **Extraction** keeps page numbers for PDFs (the basis for verifiable
  citations). DOCX has no fixed pages, so page number is `null` — an honest,
  documented limitation. Scanned/image PDFs (no text layer) fail cleanly with a
  clear reason rather than storing empty content (OCR is a future extension).
- **Chunking** is token-aware (tiktoken for sizing) with recursive splitting on
  natural boundaries and configurable size/overlap. Too-large chunks blur
  embeddings; too-small lose context — overlap preserves facts that span a
  boundary.
- **Async** via FastAPI `BackgroundTasks` for the MVP (zero extra services,
  free). Documented upgrade path: a Redis-backed queue (ARQ/Celery) for
  durability and horizontal scaling. The ingestion function is written to be
  callable from either, so the migration is contained.

## 5. Retrieval

Three selectable strategies, built incrementally so improvements are measurable:

1. **vector** — pgvector cosine search over chunk embeddings (HNSW index).
2. **hybrid** — vector + Postgres full-text keyword search, fused with
   **Reciprocal Rank Fusion**. RRF uses only rank positions, so it combines two
   score scales (cosine distance vs `ts_rank`) that are not numerically
   comparable.
3. **hybrid_rerank** — fuse a wide candidate pool, then re-score with a
   cross-encoder reranker for precision, keep the top-k.

Why retrieve-then-rerank: first-stage retrieval is fast but approximate (each
chunk was embedded in isolation); a cross-encoder scores (query, passage)
*together* and is far more precise, but too slow to run over the whole corpus —
so it only re-ranks the shortlist.

## 6. Grounded generation & citations

The prompt presents numbered, delimited sources and instructs the model to
answer only from them, cite every claim as `[n]`, and abstain otherwise. After
generation:

- `[n]` markers are mapped back to retrieved chunks; markers that reference a
  non-existent source are **rejected** (anti-fabrication).
- An answer with no valid citation is converted to an honest abstention.

Low temperature (0.2) favors faithfulness over creativity.

## 7. Agentic workflow (bounded)

A LangGraph state machine: `classify → maybe_rewrite → retrieve → assess →
(escalate → retrieve){bounded} → generate → END`.

Design principles:
- **Deterministic by default.** LLM calls only for classification and query
  rewriting (where language understanding helps). Evidence-sufficiency checking
  and strategy selection are deterministic rules — cheaper, testable, not
  subject to LLM nondeterminism.
- **Bounded.** `MAX_ATTEMPTS` caps retries; each retry *escalates* the strategy
  (vector → hybrid → hybrid+rerank) rather than repeating. No path can loop
  forever.
- **Observable.** Every node appends to a decision trace.

The honest question — *does the agent beat single-shot RAG enough to justify the
complexity?* — is answered empirically by the evaluation harness, not asserted.

## 8. Security

- JWT access tokens carry `user_id`, `org_id`, `role`; `org_id` is the tenant
  boundary used by every query. Passwords hashed with bcrypt.
- Retrieved text is untrusted: structural prompt separation + lexical defanging
  of injection trigger phrases + citation validation. Defense-in-depth, not a
  single silver bullet.
- API keys for the widget are stored only as SHA-256 hashes; the raw key is
  shown once. Each key resolves to exactly one org.
- Per-IP rate limiting (slowapi); upload type/size validation.

## 9. Observability

In-process metrics registry: latency p50/p95 per operation, request/abstention
counters, token and cost accounting, exposed at `/metrics`. Structured JSON logs
with per-request IDs. Documented production upgrade: OpenTelemetry + a metrics
backend.

## 10. Known limitations

- Stub providers are crude; real quality needs Gemini/Cohere keys.
- `BackgroundTasks` ingestion does not survive a restart (upgrade: Redis queue).
- Evaluation dataset is a small synthetic seed (expand to 100–200 for rigor).
- No OCR for scanned PDFs yet.
- In-memory metrics reset on restart (fine for a demo; use a TSDB in prod).
