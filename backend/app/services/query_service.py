import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embedders import get_embedder
from app.llm.generator import LLMGenerator, _CHAT_SYSTEM_PROMPT, _build_user_message
from app.models import KnowledgeBase, Conversation, Message
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import get_reranker
from app.schemas import ChunkResult, SourceCitation

logger = logging.getLogger(__name__)

_NO_ANSWER = "I can only answer questions related to the documents in this knowledge base. Please ask something relevant to the uploaded content."


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
        try:
            import litellm
            from app.llm.generator import _resolve_model
            _OUT_OF_CONTEXT_PROMPT = """\
You are a friendly and helpful AI assistant embedded in a document knowledge base.
Your knowledge is strictly limited to the documents uploaded by the user — you have no external knowledge beyond them.

When a user asks something that is not covered by the uploaded documents:
- Respond naturally and warmly, like a helpful friend
- Acknowledge their question genuinely
- Clearly but gently explain that this topic isn't in your document knowledge base
- Never make up information or use outside knowledge
- Keep it concise, conversational, and encouraging
- Do NOT use stiff or robotic phrasing like "I cannot find a relevant answer"
"""
            response = await litellm.acompletion(
                model=_resolve_model(kb.llm_model),
                messages=[
                    {"role": "system", "content": _OUT_OF_CONTEXT_PROMPT},
                    {"role": "user", "content": query},
                ],
                stream=True,
            )
            async for chunk in response:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield _sse("token", {"content": token})
        except Exception:
            yield _sse("token", {"content": _NO_ANSWER})
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


# ── Chat helpers ──────────────────────────────────────────────────────────────

_MAX_HISTORY = 10


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(_MAX_HISTORY)
    )
    messages = result.scalars().all()
    return list(reversed(messages))  # chronological order


async def _save_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    sources: Optional[list] = None,
    has_answer: Optional[bool] = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        has_answer=has_answer,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


def _build_chat_messages(
    history: list[Message],
    chunks: list[ChunkResult],
    user_message: str,
) -> list[dict]:
    """Build the full messages list: system prompt + conversation history + current RAG turn."""
    messages: list[dict] = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": _build_user_message(user_message, chunks)})
    return messages


# ── Chat streaming pipeline ───────────────────────────────────────────────────

async def chat_stream(
    kb: KnowledgeBase,
    conversation_id: uuid.UUID,
    user_message: str,
    db: AsyncSession,
    top_k: int = 20,
    rerank_n: int = 5,
    alpha: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Multi-turn chat RAG pipeline as an SSE async generator.

    Same event protocol as query_stream: token / sources / done / no_answer / error.
    Persists user and assistant messages to DB after generation.
    """
    # ── 1. Load conversation history ──────────────────────────────────────
    try:
        history = await _load_history(db, conversation_id)
    except Exception as exc:
        logger.exception("Failed to load chat history: %s", exc)
        history = []

    # ── 2. Embed + retrieve ───────────────────────────────────────────────
    try:
        candidates = await _embed_and_retrieve(kb, user_message, db, top_k, alpha, [], "AND")
    except Exception as exc:
        logger.exception("Chat retrieval failed for kb=%s: %s", kb.id, exc)
        yield _sse("error", {"message": f"Retrieval error: {exc}"})
        return

    # ── 3. Save user message ──────────────────────────────────────────────
    try:
        await _save_message(db, conversation_id, role="user", content=user_message)
    except Exception as exc:
        logger.warning("Could not persist user message: %s", exc)

    # ── 4. Confidence threshold ───────────────────────────────────────────
    if not candidates or candidates[0].dense_score < kb.similarity_threshold:
        logger.info(
            "No confident match for conversation=%s (best=%.3f < %.3f)",
            conversation_id,
            candidates[0].dense_score if candidates else 0.0,
            kb.similarity_threshold,
        )
        out_of_context_answer = ""
        try:
            import litellm
            from app.llm.generator import _resolve_model
            _OUT_OF_CONTEXT_PROMPT = """\
You are a professional assistant embedded in a document knowledge base.
Your knowledge is strictly limited to the documents uploaded — you have no external knowledge.
When the user asks something not covered by the documents, respond warmly and professionally,
acknowledge their question, explain the topic isn't in the knowledge base, and stay helpful.
Do NOT fabricate or use outside knowledge. Keep it concise and encouraging."""
            # Include chat history so the out-of-context response feels coherent
            ctx_messages = [{"role": "system", "content": _OUT_OF_CONTEXT_PROMPT}]
            for msg in history:
                ctx_messages.append({"role": msg.role, "content": msg.content})
            ctx_messages.append({"role": "user", "content": user_message})

            response = await litellm.acompletion(
                model=_resolve_model(kb.llm_model),
                messages=ctx_messages,
                stream=True,
            )
            async for chunk in response:
                token = chunk.choices[0].delta.content or ""
                if token:
                    out_of_context_answer += token
                    yield _sse("token", {"content": token})
        except Exception:
            out_of_context_answer = _NO_ANSWER
            yield _sse("token", {"content": _NO_ANSWER})

        try:
            await _save_message(
                db, conversation_id, role="assistant",
                content=out_of_context_answer, has_answer=False,
            )
        except Exception as exc:
            logger.warning("Could not persist assistant message: %s", exc)
        yield _sse("done", {"has_answer": False})
        return

    # ── 5. Rerank ─────────────────────────────────────────────────────────
    try:
        from app.config import settings
        reranked = await get_reranker(settings.reranker_backend).rerank(user_message, candidates, n=rerank_n)
    except Exception as exc:
        logger.warning("Reranker error, using fusion order: %s", exc)
        reranked = candidates[:rerank_n]

    # ── 6. Build multi-turn messages list ─────────────────────────────────
    chat_messages = _build_chat_messages(history, reranked, user_message)

    # ── 7. Stream answer ──────────────────────────────────────────────────
    full_answer = ""
    try:
        async for token in LLMGenerator().stream_chat(chat_messages, model=kb.llm_model):
            full_answer += token
            yield _sse("token", {"content": token})
    except Exception as exc:
        logger.exception("LLM chat generation failed: %s", exc)
        yield _sse("error", {"message": f"LLM error: {exc}"})
        return

    # ── 8. Persist assistant message + send sources ───────────────────────
    sources = _build_sources(reranked)
    sources_data = [s.model_dump() for s in sources]
    try:
        await _save_message(
            db, conversation_id, role="assistant",
            content=full_answer, sources=sources_data, has_answer=True,
        )
    except Exception as exc:
        logger.warning("Could not persist assistant message: %s", exc)

    yield _sse("sources", {"data": sources_data})
    yield _sse("done", {"has_answer": True})


# ── Chat non-streaming pipeline ───────────────────────────────────────────────

async def chat_sync(
    kb: KnowledgeBase,
    conversation_id: uuid.UUID,
    user_message: str,
    db: AsyncSession,
    top_k: int = 20,
    rerank_n: int = 5,
    alpha: float = 0.5,
) -> dict:
    """Collect full chat response before returning (non-streaming JSON)."""
    history = await _load_history(db, conversation_id)
    candidates = await _embed_and_retrieve(kb, user_message, db, top_k, alpha, [], "AND")

    await _save_message(db, conversation_id, role="user", content=user_message)

    if not candidates or candidates[0].dense_score < kb.similarity_threshold:
        await _save_message(
            db, conversation_id, role="assistant", content=_NO_ANSWER, has_answer=False,
        )
        return {"answer": _NO_ANSWER, "sources": [], "model": kb.llm_model, "has_answer": False}

    from app.config import settings
    reranked = await get_reranker(settings.reranker_backend).rerank(user_message, candidates, n=rerank_n)
    chat_messages = _build_chat_messages(history, reranked, user_message)
    answer = await LLMGenerator().complete_chat(chat_messages, model=kb.llm_model)
    sources = _build_sources(reranked)
    sources_data = [s.model_dump() for s in sources]

    await _save_message(
        db, conversation_id, role="assistant",
        content=answer, sources=sources_data, has_answer=True,
    )

    return {"answer": answer, "sources": sources_data, "model": kb.llm_model, "has_answer": True}
