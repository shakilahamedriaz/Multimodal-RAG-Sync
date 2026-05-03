import asyncio
import logging
from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis

from app.chunkers import get_chunker
from app.config import settings
from app.database import AsyncSessionLocal
from app.embedders import get_embedder
from app.models import Chunk, Document, DocumentStatus, KnowledgeBase
from app.parsers import parse_document
from app.storage import load_file

logger = logging.getLogger(__name__)

_JOB_TTL_SECONDS = 86_400  # 24 h


# ── Redis helpers (failures never abort ingestion) ───────────────────────────

async def _redis_set_status(redis, job_id: str, status: str, message: str = "") -> None:
    try:
        await redis.hset(
            f"job:{job_id}",
            mapping={
                "status": status,
                "message": message,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        await redis.expire(f"job:{job_id}", _JOB_TTL_SECONDS)
    except Exception as exc:
        logger.debug("Redis status update skipped: %s", exc)


async def get_job_status_from_redis(job_id: str) -> dict | None:
    """Return {status, message, updated_at} from Redis, or None on miss/error."""
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        data = await redis.hgetall(f"job:{job_id}")
        await redis.aclose()
        return data if data else None
    except Exception:
        return None


# ── Retry helper ─────────────────────────────────────────────────────────────

async def _with_retry(fn, *args, max_retries: int = 3, base_delay: float = 2.0):
    for attempt in range(max_retries):
        try:
            return await fn(*args)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = base_delay * (2 ** attempt)
            logger.warning("Retry %d/%d for %s in %.1fs: %s", attempt + 1, max_retries, fn.__name__, wait, exc)
            await asyncio.sleep(wait)


# ── Status updater ────────────────────────────────────────────────────────────

async def _update_status(
    db,
    redis,
    doc: Document,
    status: DocumentStatus,
    message: str = "",
) -> None:
    doc.status = status
    await db.flush()
    await _redis_set_status(redis, str(doc.id), status, message)
    logger.info("doc=%s status=%s", doc.id, status)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def ingest_document(doc_id: UUID) -> None:
    """Full ingestion pipeline: parse → chunk → embed → pgvector index.

    Designed to run as a FastAPI BackgroundTask. Creates its own DB session
    and Redis connection so it is fully decoupled from the request context.
    """
    redis = None
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        logger.debug("Redis unavailable — job status will only be tracked in DB")

    async with AsyncSessionLocal() as db:
        doc: Document | None = await db.get(Document, doc_id)
        if doc is None:
            logger.error("ingest_document: document %s not found — skipping", doc_id)
            return

        kb: KnowledgeBase | None = await db.get(KnowledgeBase, doc.kb_id)
        if kb is None:
            logger.error("ingest_document: KB %s not found for doc %s — skipping", doc.kb_id, doc_id)
            return

        try:
            logger.info("Ingestion started: doc=%s file=%r kb=%s", doc_id, doc.filename, doc.kb_id)

            # ── 1. PARSING ───────────────────────────────────────────────
            await _update_status(db, redis, doc, DocumentStatus.PARSING)
            content = await load_file(doc.storage_key)
            parsed = await _with_retry(parse_document, content, doc.mime_type)
            doc.page_count = parsed.page_count
            await db.flush()

            # ── 2. CHUNKING ──────────────────────────────────────────────
            await _update_status(db, redis, doc, DocumentStatus.CHUNKING)
            chunker = get_chunker(kb.chunking_strategy)
            raw_chunks = await asyncio.to_thread(
                chunker.chunk, parsed, kb.chunk_size, kb.chunk_overlap
            )
            if not raw_chunks:
                raise ValueError(
                    "Document produced no chunks — it may be empty, image-only, or corrupt"
                )

            # ── 3. EMBEDDING ─────────────────────────────────────────────
            await _update_status(db, redis, doc, DocumentStatus.EMBEDDING)
            embedder = get_embedder(kb.embedding_model)
            texts = [c.text for c in raw_chunks]
            embeddings: list[list[float]] = await _with_retry(embedder.embed, texts)

            if len(embeddings) != len(raw_chunks):
                raise ValueError(
                    f"Embedding count mismatch: expected {len(raw_chunks)}, got {len(embeddings)}"
                )

            # ── 4. INDEXING ──────────────────────────────────────────────
            chunk_records = [
                Chunk(
                    document_id=doc.id,
                    kb_id=doc.kb_id,
                    chunk_text=raw_chunks[i].text,
                    chunk_type=raw_chunks[i].chunk_type,
                    page_number=raw_chunks[i].page_number,
                    chunk_index=raw_chunks[i].chunk_index,
                    token_count=raw_chunks[i].token_count,
                    embedding_model=kb.embedding_model,
                    embedding=embeddings[i],
                    chunk_metadata=raw_chunks[i].chunk_metadata,
                )
                for i in range(len(raw_chunks))
            ]
            db.add_all(chunk_records)
            doc.chunk_count = len(chunk_records)
            doc.ingested_at = datetime.utcnow()
            await _update_status(db, redis, doc, DocumentStatus.INDEXED)
            await db.commit()

            logger.info(
                "Ingestion complete: doc=%s chunks=%d pages=%d",
                doc_id,
                len(chunk_records),
                parsed.page_count,
            )

        except Exception as exc:
            logger.exception("Ingestion failed: doc=%s error=%s", doc_id, exc)
            doc.error_message = str(exc)[:1000]
            await _update_status(db, redis, doc, DocumentStatus.FAILED, str(exc)[:500])
            await db.commit()

        finally:
            if redis:
                try:
                    await redis.aclose()
                except Exception:
                    pass
