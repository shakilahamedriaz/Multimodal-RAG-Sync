# Multimodal RAG Knowledge Base — Task Tracker

> Status key: `[ ]` Not started · `[~]` In progress · `[x]` Done · `[!]` Blocked

---

## Phase 1 — Foundation (Config + DB + KB CRUD)
> Goal: Server boots, connects to PostgreSQL, Knowledge Base CRUD works via API.

- [x] Update Task.md with 5-phase breakdown
- [x] `backend/pyproject.toml` — all Python dependencies
- [x] `backend/.env.example` + root `.env.example` — all required env vars documented
- [x] `backend/app/config.py` — Pydantic Settings, load all env vars
- [x] `backend/app/database.py` — async SQLAlchemy + pgvector extension setup
- [x] `backend/app/models.py` — ORM models: KnowledgeBase, Document, Chunk
- [x] `backend/app/main.py` — FastAPI app, CORS, lifespan, router registration
- [x] `backend/app/routes/health.py` — `GET /health`
- [x] `backend/app/routes/knowledge_bases.py` — `POST /kb`, `GET /kb`, `GET /kb/{id}`, `PATCH /kb/{id}`, `DELETE /kb/{id}`
- [x] `backend/app/routes/documents.py` — `GET /kb/{id}/documents`, `DELETE /kb/{id}/documents/{doc_id}` (upload → Phase 2)
- [x] `backend/app/routes/query.py` — 501 stub placeholder

---

## Phase 2 — Document Ingestion Pipeline
> Goal: Upload a PDF/DOCX → it gets parsed, chunked, embedded, indexed. Status polling works.

- [x] `backend/app/schemas.py` — internal DTOs: ParsedPage, ParsedDocument, TextChunk
- [x] `backend/app/storage.py` — compute_hash, save_file, load_file, delete_file (local filesystem)
- [x] `backend/app/parsers/pdf_parser.py` — PyMuPDF text + page extraction
- [x] `backend/app/parsers/docx_parser.py` — python-docx paragraph/heading extraction + TextParser
- [x] `backend/app/parsers/__init__.py` — dispatcher by MIME type (asyncio.to_thread)
- [x] `backend/app/chunkers/fixed_size.py` — token-based split + overlap (tiktoken)
- [x] `backend/app/chunkers/recursive.py` — recursive separator split + overlap
- [x] `backend/app/chunkers/__init__.py` — factory keyed by strategy name
- [x] `backend/app/embedders/openai_embedder.py` — text-embedding-3-small/large, batched, ordered
- [x] `backend/app/embedders/__init__.py` — factory keyed by model name
- [x] `backend/app/services/ingestion_service.py` — parse→chunk→embed→index; Redis status; 3x retry with exponential backoff
- [x] `backend/app/routes/documents.py` — `POST /kb/{id}/documents` (multi-file, 202 async)
- [x] `backend/app/routes/documents.py` — `GET /kb/{id}/status/{job_id}` (Redis fast path → DB fallback)
- [x] `backend/app/routes/documents.py` — `DELETE /kb/{id}/documents/{doc_id}`
- [x] SHA-256 deduplication — blocks re-upload of identical file within same KB

---

## Phase 3 — Retrieval & Query Engine
> Goal: Ask a question → get a streamed, sourced answer from your documents.

- [x] `backend/app/schemas.py` — added `ChunkResult` (retrieval DTO) + `SourceCitation` (Pydantic, serialisable)
- [x] `backend/app/retrieval/hybrid_retriever.py` — dense pgvector cosine + BM25s sparse, alpha-blend fusion, safe metadata filtering
- [x] `backend/app/retrieval/reranker.py` — lazy-loaded cross-encoder (ms-marco-MiniLM-L-6-v2), async thread pool
- [x] `backend/app/llm/generator.py` — LiteLLM `acompletion`: stream() + complete(), system prompt with citation rules
- [x] `backend/app/services/query_service.py` — query_stream (SSE generator) + query_sync; full pipeline with logging
- [x] `backend/app/routes/query.py` — `POST /kb/{id}/query` JSON + SSE (206), FilterCondition validation, documented SSE protocol
- [x] Confidence threshold: dense_score < kb.similarity_threshold → no_answer event, no LLM call
- [x] Metadata filtering: eq/ne/gt/gte/lt/lte/in/nin with AND/OR, field whitelist prevents SQL injection
- [x] `backend/app/database.py` — HNSW index on `chunks.embedding` (WHERE embedding IS NOT NULL)

---

## Phase 4 — Multimodal + Advanced Features
> Goal: Images, tables, local models, auth, rate limiting all work.

- [x] `backend/app/parsers/image_parser.py` — GPT-4o vision captioning, base64 data URL
- [x] `backend/app/parsers/table_parser.py` — PyMuPDF find_tables() → GFM markdown
- [x] `backend/app/chunkers/semantic.py` — sentence-transformers cosine grouping (local, process-cached)
- [x] `backend/app/chunkers/page_level.py` — one chunk per page, preserves chunk_type
- [x] `backend/app/embedders/sentence_transformer_embedder.py` — BAAI/bge-large local, asyncio.to_thread
- [x] `backend/app/retrieval/reranker.py` — Cohere Rerank v3.5 + local cross-encoder factory
- [x] `backend/app/services/query_service.py` — uses get_reranker(settings.reranker_backend)
- [x] `backend/app/parsers/__init__.py` — image MIME types routed to ImageParser; PDF → TableAwarePDFParser
- [x] `backend/app/chunkers/__init__.py` — semantic + page_level added to registry
- [x] `backend/app/embedders/__init__.py` — ST models routed to SentenceTransformerEmbedder
- [x] `backend/app/schemas.py` — chunk_type field on ParsedPage + TextChunk
- [x] API key auth middleware — Bearer token, bcrypt-hashed, prefix lookup, dev bypass
- [x] `backend/app/routes/auth.py` — POST/GET/DELETE /auth/keys
- [x] Rate limiting middleware (slowapi) in main.py
- [x] Document status state machine: QUEUED → PARSING → CHUNKING → EMBEDDING → INDEXED / FAILED
- [!] CLIP multimodal embeddings — deferred (heavy deps, Vector(1536) dim mismatch)

---

## Phase 5 — Frontend + Tests + Evaluation
> Goal: Working web UI, 80%+ test coverage, Ragas evaluation passing.

### Next.js Frontend
- [x] `frontend/package.json` — Next.js 14, Tailwind, TypeScript
- [x] `frontend/tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.js`
- [x] `frontend/src/app/globals.css`, `layout.tsx` — root layout, Inter font, nav bar
- [x] `frontend/src/app/page.tsx` — KB dashboard (list + create modal)
- [x] `frontend/src/app/kb/[id]/page.tsx` — KB detail: documents, upload, delete
- [x] `frontend/src/app/kb/[id]/query/page.tsx` — streaming query interface
- [x] `frontend/src/components/KnowledgeBaseCard.tsx` — card with inline delete
- [x] `frontend/src/components/DocumentUploader.tsx` — drag-and-drop, polling, status icons
- [x] `frontend/src/components/QueryInput.tsx` — form with advanced options (top-K, alpha)
- [x] `frontend/src/components/AnswerPanel.tsx` — streaming markdown + cursor
- [x] `frontend/src/components/CitationsPanel.tsx` — collapsible source cards
- [x] `frontend/src/lib/api.ts` — typed API client, SSE stream helper, Bearer auth

### Tests
- [x] `backend/tests/conftest.py` — shared fixtures, env stubs
- [x] `backend/tests/test_parsers.py` — TextParser, TableAwarePDFParser, DOCXParser, MIME dispatch
- [x] `backend/tests/test_chunkers.py` — FixedSize, Recursive, PageLevel, factory
- [x] `backend/tests/test_query.py` — _build_sources, _sse, filter builder, reranker factory, storage
- [ ] >= 80% unit test coverage (`pytest --cov`) — run after env setup

### Evaluation
- [x] `eval/sample_questions.json` — seed QA pairs (expand with domain questions)
- [x] `eval/evaluate.py` — Ragas pipeline: Faithfulness >= 0.85, Answer Relevance >= 0.80

### Observability
- [!] OpenTelemetry tracing — pyproject.toml has dep, wiring deferred
- [!] Prometheus metrics — pyproject.toml has dep, wiring deferred
- [!] Structured JSON logging — structlog dep present, wiring deferred

---

## Completed

- [x] Project scaffold (58 files)
- [x] SRS document
- [x] `.claude/Task.md` created
- [x] `.claude/feedback.md` created
- [x] **Phase 1 complete** — pyproject.toml, .env.example, config, database, models, main, all routes (health + KB CRUD + docs list + query stub)
- [x] **Phase 2 complete** — schemas, storage, PDF/DOCX/text parsers, fixed-size + recursive chunkers, OpenAI embedder, full ingestion service with retry + Redis status, upload/status/delete endpoints
- [x] **Phase 3 complete** — hybrid retriever (dense+sparse+fusion), cross-encoder reranker, LiteLLM generator, full query pipeline (stream + sync), confidence threshold, metadata filtering, HNSW index
- [x] **Phase 4 complete** — image captioning (GPT-4o), table-aware PDF parser, semantic + page-level chunkers, local ST embedder, Cohere reranker, API key auth, slowapi rate limiting
- [x] **Phase 5 complete** — Next.js 14 frontend (dashboard + KB detail + streaming query), typed API client, SSE stream helper, 3 test suites (parsers/chunkers/query+storage), Ragas evaluation pipeline

---

_Last updated: 2026-05-03_
