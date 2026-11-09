# Nexus AI

**Agentic RAG knowledge intelligence platform.** Upload documents, ask
questions, and get evidence-grounded answers with verifiable citations. Built as
a production-shaped portfolio project: real retrieval quality, a bounded agentic
workflow, measurable evaluation, multi-tenant security, and a deployable stack.

> Not a chatbot wrapped around an LLM. The emphasis is on retrieval quality,
> reliable reasoning, honest evaluation, and production engineering.

---

## Highlights

- **Hybrid retrieval**: pgvector semantic search + Postgres full-text keyword
  search, fused with Reciprocal Rank Fusion, with an optional cross-encoder
  reranker. All behind swappable provider interfaces.
- **Bounded agentic workflow** (LangGraph): classify → optional query rewrite →
  retrieve → assess evidence → bounded escalate+retry → grounded generation →
  citation validation. No unbounded loops.
- **Grounded answers with verifiable citations** and honest abstention when
  evidence is insufficient (fabricated citations are rejected).
- **Reproducible evaluation**: Recall@k, MRR, nDCG@k, passage-hit-rate, plus
  generation-quality proxies — comparing vector vs hybrid vs hybrid+rerank.
- **Multi-tenant security**: JWT auth, org isolation enforced in SQL, RBAC,
  prompt-injection defenses, API keys for an embeddable widget, rate limiting.
- **Swappable providers**: runs fully offline/free on deterministic stubs, or on
  Gemini (LLM + embeddings) and Cohere (rerank) by setting API keys — no code
  change.
- **Deployable**: Docker + Compose, CI (lint + tests + build), a React
  dashboard, and a framework-agnostic embeddable chat widget.

## Architecture

```
┌──────────────────────┐        ┌──────────────────────────────────────┐
│ React dashboard (SPA)│        │ Embeddable widget (standalone script) │
│ auth · docs · chat   │        │ Shadow DOM · X-API-Key                │
└──────────┬───────────┘        └──────────────────┬────────────────────┘
           │ JWT                                   │ public API key
           ▼                                       ▼
        ┌────────────────────────────────────────────────────┐
        │ FastAPI backend (modular monolith)                   │
        │  auth · documents · chat · widget · metrics          │
        │  retrieval: vector | keyword | hybrid(RRF) | rerank  │
        │  agent: bounded LangGraph workflow                   │
        │  providers: LLM | Embedding | Reranker (swappable)   │
        └───┬───────────────────────┬──────────────────┬───────┘
            │ async ingestion       │ API calls        │ SQL (org-scoped)
            ▼                       ▼                  ▼
     BackgroundTasks         Gemini / Cohere     PostgreSQL + pgvector
     (extract→chunk→embed)   (or stubs)          + full-text search
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and
trade-offs, and [`docs/EVALUATION.md`](docs/EVALUATION.md) for the benchmark.

## Tech stack

| Layer      | Choice                                                        |
|------------|---------------------------------------------------------------|
| Backend    | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 (async)       |
| Data       | PostgreSQL + pgvector + full-text search (Neon-hosted)        |
| Retrieval  | Hybrid (vector + keyword) + RRF + cross-encoder reranker      |
| Agent      | LangGraph (bounded state machine)                             |
| AI (demo)  | Gemini (LLM + embeddings), Cohere (rerank) — stubs by default |
| Frontend   | React + TypeScript + Vite                                     |
| Infra      | Docker, Docker Compose, GitHub Actions CI                     |

## Prerequisites

| Tool    | Version      |
|---------|--------------|
| Python  | 3.12 or 3.13 |
| Node.js | 22 LTS       |
| Docker  | current (optional, for containerized run) |
| Postgres| a Neon free database (connection string) |

## Quick start (local, no Docker)

```powershell
# 1. Configure
Copy-Item .env.example .env        # set DATABASE_URL (Neon). Keys optional.

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head               # create tables + pgvector + FTS indexes
uvicorn app.main:app --reload      # http://localhost:8000/docs

# 3. Frontend (second terminal)
cd frontend
Copy-Item .env.example .env
npm install
npm run dev                        # http://localhost:5173
```

Register an account in the UI, upload a PDF/DOCX, wait for `ready`, then ask.

## Quick start (Docker, full stack)

```powershell
Copy-Item .env.example .env        # set DATABASE_URL
docker compose up --build
# Frontend: http://localhost:5173   Backend: http://localhost:8000
```

The backend container runs migrations on startup, then serves the API.

## Running without API keys (default)

With no `GEMINI_API_KEY` / `COHERE_API_KEY`, the app uses deterministic **stub**
providers: everything runs offline and free, and the full pipeline (ingestion →
hybrid retrieval → agentic workflow → citations) works end to end. Stub
embeddings are intentionally crude, so answer quality is limited — set real keys
for production-quality results. The provider factory swaps implementations by
config alone; no code changes.

## Tests

```powershell
cd backend
pytest -q -m "not integration"   # fast unit suite (no DB)
pytest -q                        # + integration tests (needs DATABASE_URL)
```

## Evaluation

```powershell
cd backend
python -m app.eval.runner        # writes eval/reports/compare_*.json
```

Compares `vector`, `hybrid`, and `hybrid_rerank` on the seed dataset. See
[`docs/EVALUATION.md`](docs/EVALUATION.md) for methodology, results, and honest
limitations.

## Embeddable widget

A standalone, framework-agnostic script (`widget/nexus-widget.js`) mounts a chat
bubble in any website via Shadow DOM. An org admin creates a public API key
(`POST /widget/keys`), and the host page embeds:

```html
<script src="/nexus-widget.js"
        data-api-base="https://your-api"
        data-api-key="nxs_PUBLIC_KEY"></script>
```

Open `widget/demo.html` to see it in action. The key resolves server-side to one
organization, so tenant isolation holds for anonymous traffic.

## Security

- JWT auth; passwords hashed with bcrypt (never stored/logged raw).
- Tenant isolation enforced in SQL `WHERE org_id = ...` on every query; cross-org
  access returns 404 (no existence leak). Verified by integration tests.
- Retrieved document text is treated as untrusted: structured prompt + injection
  defanging + citation validation + low temperature.
- Upload type/size validation, per-IP rate limiting.
- Secrets via environment only; `.env` git-ignored.

## Project layout

```
backend/   FastAPI app (auth, documents, retrieval, agent, eval, providers)
frontend/  React + TypeScript dashboard
widget/    Embeddable chat script + demo page
eval/      Evaluation dataset + reports
docs/      Architecture + evaluation write-ups
```

## Status & roadmap

Milestones 0–9 implemented: foundation, ingestion, baseline RAG, hybrid
retrieval, agentic workflow, evaluation + observability, multi-tenant security,
frontend + widget, deployment. See `docs/` for details and known limitations.
