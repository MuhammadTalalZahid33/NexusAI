# Nexus AI

Agentic RAG knowledge intelligence platform. Upload documents, ask questions,
get evidence-grounded answers with verifiable citations.

> **Status:** Milestone 1 (project foundation). Backend skeleton with health
> checks, env-driven config, structured logging, tests, Docker, and CI.

## Architecture (target)

A modular monolith: one FastAPI backend, one PostgreSQL database (with
`pgvector` for vector search and full-text search for keyword search), a React
dashboard, and an embeddable widget. AI inference runs through swappable
provider interfaces (Gemini for generation + embeddings, Cohere for reranking),
so a free-tier key can be replaced by a paid or self-hosted provider via config.

See `docs/` (added in later milestones) for the full architecture and data flow.

## Repository layout

```
NexusAI/
├─ backend/          FastAPI app (API, RAG, ingestion, eval)
├─ frontend/         React dashboard (added in Milestone 1 step 5)
├─ widget/           Embeddable chat script (later)
├─ eval/             Evaluation datasets + reports (later)
├─ docker-compose.yml
├─ .env.example
└─ .github/workflows/ci.yml
```

## Prerequisites

| Tool            | Version        | Needed for                         |
|-----------------|----------------|------------------------------------|
| Python          | 3.12 or 3.13   | backend                            |
| Node.js         | 22 LTS or 24   | frontend                           |
| Docker Desktop  | current        | containerized run (optional in M1) |
| Git             | any recent     | version control                    |

A managed Postgres (Neon) and a Gemini API key are introduced in later
milestones; they are **not** required to run Milestone 1.

## Quick start (backend, local)

```powershell
# From the repo root
Copy-Item .env.example .env        # fill in later; defaults are fine for M1

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Run the API
uvicorn app.main:app --reload

# Verify
#   http://localhost:8000/health   -> {"status":"ok",...}
#   http://localhost:8000/docs     -> interactive API docs
```

### Run the tests

```powershell
cd backend
pytest -q
```

### Lint / format

```powershell
cd backend
ruff check .
ruff format .
```

## Quick start (frontend, local)

The frontend is a Vite + React + TypeScript app. It talks to the backend
through a single typed API client (`src/api/client.ts`) and reads the backend
URL from `VITE_API_BASE_URL`.

```powershell
cd frontend
Copy-Item .env.example .env   # defaults to http://localhost:8000
npm install
npm run dev
```

Open http://localhost:5173. With the backend also running, the page shows a
live "Backend status: Healthy" card populated from the `/health` endpoint.

## Quick start (backend, Docker)

```powershell
# From the repo root (needs a .env file)
docker compose up --build
# Then open http://localhost:8000/health
```

## Environment variables

Copy `.env.example` to `.env`. For Milestone 1 the defaults are sufficient;
`DATABASE_URL` and provider keys are introduced later. Never commit `.env`.

## License

TBD.
