import json
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.embedders import get_embedder
from app.llm.generator import LLMGenerator
from app.models import KnowledgeBase
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import get_reranker
from app.schemas import ChunkResult, SourceCitation

logger = logging.getLogger(__name__)

_NO_ANSWER = "I cannot find a relevant answer in the available documents."


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_sources(chunks: list[ChunkResult]) -> list[SourceCitation]:
    return [
        SourceCitation(
            source_index=i + 1,
            chunk_id=str(chunk.chunk_id),
            document_id=str(chunk.document_id),
            filename=chunk.filename,
            page_number=chunk.page_number,
            excerpt=(chunk.chunk_text[:300] + "…") if len(chunk.chunk_text) > 300 else chunk.chunk_text,
            similarity_score=round(chunk.dense_score, 4),
            rerank_score=round(chunk.rerank_score, 4) if chunk.rerank_score is not None else None,
        )
        for i, chunk in enumerate(chunks)
    ]


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def _embed_and_retrieve(
    kb: KnowledgeBase,
    query: str,
    db: AsyncSession,
    top_k: int,
    alpha: float,
    filters: list[dict],
    filter_op: str,
) -> list[ChunkResult]:
    embedder = get_embedder(kb.embedding_model)
    vectors = await embedder.embed([query])
    query_vector = vectors[0]

    retriever = HybridRetriever(db)
    return await retriever.retrieve(
        kb_id=kb.id,
        query=query,
        query_vector=query_vector,
        top_k=top_k,
        alpha=alpha,
        filters=filters,
        filter_op=filter_op,
    )


# ── Streaming pipeline ────────────────────────────────────────────────────────

async def query_stream(
    kb: KnowledgeBase,
    query: str,
    db: AsyncSession,
    top_k: int = 20,
    rerank_n: int = 5,
    alpha: float = 0.5,
    filters: Optional[list[dict]] = None,
    filter_op: str = "AND",
) -> AsyncGenerator[str, None]:
    """Full RAG pipeline as an SSE async generator.

    Event protocol:
      {"type": "token",     "content": "..."}   — one per LLM token
      {"type": "sources",   "data": [...]}       — after answer completes
      {"type": "done",      "has_answer": bool}  — terminal event
      {"type": "no_answer", "message": "..."}    — when retrieval confidence is low
      {"type": "error",     "message": "..."}    — on unexpected failure
    """
    filters = filters or []

    # ── 1. Embed + retrieve ───────────────────────────────────────────────
    try:
        candidates = await _embed_and_retrieve(kb, query, db, top_k, alpha, filters, filter_op)
    except Exception as exc:
        logger.exception("Retrieval failed for kb=%s: %s", kb.id, exc)
        yield _sse("error", {"message": f"Retrieval error: {exc}"})
        return

    # ── 2. Confidence threshold ───────────────────────────────────────────
    if not candidates or candidates[0].dense_score < kb.similarity_threshold:
        logger.info("No confident match for kb=%s query=%r (best=%.3f < %.3f)",
                    kb.id, query[:80],
                    candidates[0].dense_score if candidates else 0.0,
                    kb.similarity_threshold)
        yield _sse("no_answer", {"message": _NO_ANSWER})
        yield _sse("done", {"has_answer": False})
        return

    # ── 3. Rerank ─────────────────────────────────────────────────────────
    try:
        from app.config import settings
        reranked = await get_reranker(settings.reranker_backend).rerank(query, candidates, n=rerank_n)
    except Exception as exc:
        logger.warning("Reranker error, using fusion order: %s", exc)
        reranked = candidates[:rerank_n]

    # ── 4. Stream answer ──────────────────────────────────────────────────
    try:
        async for token in LLMGenerator().stream(query, reranked, model=kb.llm_model):
            yield _sse("token", {"content": token})
    except Exception as exc:
        logger.exception("LLM generation failed for kb=%s: %s", kb.id, exc)
        yield _sse("error", {"message": f"LLM error: {exc}"})
        return

    # ── 5. Send sources + done ────────────────────────────────────────────
    sources = _build_sources(reranked)
    yield _sse("sources", {"data": [s.model_dump() for s in sources]})
    yield _sse("done", {"has_answer": True})


# ── Non-streaming pipeline ────────────────────────────────────────────────────

async def query_sync(
    kb: KnowledgeBase,
    query: str,
    db: AsyncSession,
    top_k: int = 20,
    rerank_n: int = 5,
    alpha: float = 0.5,
    filters: Optional[list[dict]] = None,
    filter_op: str = "AND",
) -> dict:
    """Collect the full answer before returning (non-streaming JSON)."""
    filters = filters or []

    candidates = await _embed_and_retrieve(kb, query, db, top_k, alpha, filters, filter_op)

    if not candidates or candidates[0].dense_score < kb.similarity_threshold:
        return {
            "answer": _NO_ANSWER,
            "sources": [],
            "model": kb.llm_model,
            "has_answer": False,
            "query": query,
        }

    from app.config import settings
    reranked = await get_reranker(settings.reranker_backend).rerank(query, candidates, n=rerank_n)
    answer = await LLMGenerator().complete(query, reranked, model=kb.llm_model)
    sources = _build_sources(reranked)

    return {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "model": kb.llm_model,
        "has_answer": True,
        "query": query,
    }
