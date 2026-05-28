from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import create_tables
from app.routes import health, knowledge_bases, documents, query, chat
from app.routes import auth as auth_routes

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    _prewarm_models()
    yield


def _prewarm_models() -> None:
    """Load ML models into memory at startup so the first query is not slow."""
    try:
        from app.embedders.sentence_transformer_embedder import SentenceTransformerEmbedder
        SentenceTransformerEmbedder("all-MiniLM-L6-v2")._get_model()
        print("[startup] Embedder ready: all-MiniLM-L6-v2", flush=True)
    except Exception as exc:
        print(f"[startup] Embedder pre-warm failed: {exc}", flush=True)
    try:
        from app.retrieval.reranker import CrossEncoderReranker
        CrossEncoderReranker._load_model()
        print("[startup] Reranker ready: cross-encoder/ms-marco-MiniLM-L-6-v2", flush=True)
    except Exception as exc:
        print(f"[startup] Reranker pre-warm failed: {exc}", flush=True)


app = FastAPI(
    title="Multimodal RAG Knowledge Base API",
    version="0.2.0",
    description="Intelligent multimodal document retrieval and Q&A with source attribution",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(auth_routes.router)
app.include_router(knowledge_bases.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
