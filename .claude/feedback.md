# Project Feedback & Requirements Notes

> Running notes for the developer (shakilahamedriaz). Updated as the project evolves.

---

## Critical Decisions Required Before You Start

### 1. No Docker — Local Services Setup
You said no Docker. That means you need these services installed locally on your machine:

| Service | Purpose | How to get it (Windows) |
|---|---|---|
| **PostgreSQL 15+** | Primary DB + pgvector extension | https://www.postgresql.org/download/windows/ — enable pgvector via `CREATE EXTENSION vector;` |
| **Redis 7+** | Job queue (Redis Streams) + caching | https://github.com/tporadowski/redis/releases (Windows port) or WSL2 Redis |
| **Python 3.11** | Backend runtime | python.org or pyenv-win |
| **Node.js 20 LTS** | Frontend runtime | nodejs.org |

> MinIO (object storage) can run as a standalone .exe without Docker — download from https://min.io/download. Or skip it for now and use local filesystem storage in dev, then wire S3 for prod.

---

## Architecture Feedback

### Vector DB Choice — Use pgvector First
The SRS lists Weaviate, Pinecone, or pgvector. **Start with pgvector** (PostgreSQL extension) because:
- No extra service to run — same PostgreSQL you already need
- Supports HNSW indexes natively since pg 0.5.0
- Easy to migrate later if you outgrow it

### Chunking Strategy — Default Recommendation
Start with **recursive** as the default — it respects natural boundaries (paragraphs, sentences) and produces higher-quality chunks than fixed-size for most document types. Fixed-size is simpler to implement first as a baseline.

### Embedding Model — Start Small
Use `text-embedding-3-small` (OpenAI) to get the pipeline running end-to-end. It's cheap and fast. Add sentence-transformer local fallback in Phase 2.

### LLM Routing via LiteLLM
LiteLLM is the right call here. One unified `completion()` call works for GPT-4o, Claude, Mistral. Use it from day one — don't hardcode OpenAI then refactor.

---

## Required Environment Variables
These must be in `backend/.env` before the server starts:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rag_db

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI (required for embedding + LLM)
OPENAI_API_KEY=sk-...

# Anthropic (optional, for Claude models)
ANTHROPIC_API_KEY=sk-ant-...

# Cohere (optional, for reranking)
COHERE_API_KEY=...

# Object Storage (use local path for dev, S3 for prod)
STORAGE_BACKEND=local          # or "s3" / "minio"
LOCAL_STORAGE_PATH=./storage

# Security
API_KEY_SECRET=<random 32-char string>

# App
APP_ENV=development
LOG_LEVEL=INFO
```

---

## Things to Avoid

- **No Docker** — confirmed by user. Use local installs only.
- **Don't hardcode model names** — always read from KB config or env var so switching models doesn't require code changes.
- **Don't block the async event loop** — all I/O in FastAPI routes must be `async`. Use `asyncpg` for DB, `httpx` for HTTP calls.
- **Don't skip the job queue** — even in dev. The ingestion pipeline is async by design; trying to do it synchronously in the request will timeout on large PDFs.

---

## Open Questions (Need Your Input)

1. **Authentication scope** — Is this a single-user tool (one API key in .env) or multi-tenant (users sign up, get their own API keys)? The SRS says multi-tenant but that adds auth complexity.
2. **Primary LLM for MVP** — GPT-4o (costs money per query) or local Ollama (free, slower)? Affects default config.
3. **Image parsing priority** — GPT-4V for image captioning is expensive. Should image support be in Phase 1 or deferred to Phase 2?
4. **Object storage** — Local filesystem for dev is fine, but what's the prod target — AWS S3 or a self-hosted solution?
5. **Frontend first or API first?** — Recommend API first (backend fully working with curl/Postman), then build UI. Agree?

---

## SRS Deviations Planned

| Item in SRS | Planned deviation | Reason |
|---|---|---|
| Docker Compose for dev | Local installs (PostgreSQL, Redis) | User preference |
| Kubernetes for prod | Out of scope for now | No infra defined yet |
| AWS S3 object storage | Local filesystem (dev) → S3 later | No cloud infra yet |

---

## Quality Checkpoints

Before marking a phase complete, verify:
- [ ] All endpoints return correct HTTP status codes (201 for create, 204 for delete, 422 for validation errors)
- [ ] Ingestion pipeline handles corrupt/empty files without crashing
- [ ] Query endpoint streams correctly (SSE) — test with `curl -N`
- [ ] No blocking I/O on the async event loop (profile with `async-profiler` or log slow queries)
- [ ] pgvector HNSW index created on `chunks.embedding` column (critical for p99 < 100ms)
- [ ] Unit test coverage >= 80% (`pytest --cov`)

---

_Last updated: 2026-05-03_
