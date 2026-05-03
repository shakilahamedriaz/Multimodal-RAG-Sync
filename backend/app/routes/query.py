import json
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import KnowledgeBase
from app.services.query_service import query_stream, query_sync

router = APIRouter(prefix="/kb", tags=["query"])


# ── Request schema ────────────────────────────────────────────────────────────

class FilterCondition(BaseModel):
    field: str
    op: str = Field(..., pattern="^(eq|ne|gt|gte|lt|lte|in|nin)$")
    value: Any

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        allowed = {"page_number", "chunk_type", "chunk_index", "document_id"}
        if v not in allowed:
            raise ValueError(f"Filter field must be one of: {sorted(allowed)}")
        return v


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(20, ge=5, le=100, description="Candidates fetched before reranking")
    rerank_n: int = Field(5, ge=1, le=20, description="Final chunks passed to the LLM")
    alpha: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Dense weight. 1.0 = dense-only, 0.0 = sparse-only",
    )
    stream: bool = Field(False, description="Use SSE streaming response")
    filters: list[FilterCondition] = Field(default_factory=list)
    filter_op: str = Field("AND", pattern="^(AND|OR)$")


# ── Response schema (non-streaming) ──────────────────────────────────────────

class SourceCitationOut(BaseModel):
    source_index: int
    chunk_id: str
    document_id: str
    filename: str
    page_number: Optional[int]
    excerpt: str
    similarity_score: float
    rerank_score: Optional[float]


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitationOut]
    model: str
    has_answer: bool
    query: str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/{kb_id}/query",
    response_model=QueryResponse,
    responses={
        200: {"description": "JSON answer (stream=false)"},
        206: {
            "description": "SSE stream (stream=true)",
            "content": {
                "text/event-stream": {
                    "example": (
                        'data: {"type":"token","content":"Based"}\n\n'
                        'data: {"type":"sources","data":[...]}\n\n'
                        'data: {"type":"done","has_answer":true}\n\n'
                    )
                }
            },
        },
    },
)
async def query_kb(
    kb_id: UUID,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """RAG query against a knowledge base.

    **Non-streaming** (`stream=false`): Returns a complete JSON response.

    **Streaming** (`stream=true`): Returns a `text/event-stream` response.
    Each line is `data: <json>\\n\\n`. Event types:
    - `token` — LLM output token
    - `sources` — source citations (sent after all tokens)
    - `done` — terminal event
    - `no_answer` — retrieval confidence below threshold
    - `error` — unexpected failure
    """
    kb: KnowledgeBase | None = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    filter_dicts = [f.model_dump() for f in payload.filters]

    if payload.stream:
        async def event_generator():
            try:
                async for event in query_stream(
                    kb=kb,
                    query=payload.query,
                    db=db,
                    top_k=payload.top_k,
                    rerank_n=payload.rerank_n,
                    alpha=payload.alpha,
                    filters=filter_dicts,
                    filter_op=payload.filter_op,
                ):
                    yield event
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        return StreamingResponse(
            event_generator(),
            status_code=206,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering for streaming
            },
        )

    result = await query_sync(
        kb=kb,
        query=payload.query,
        db=db,
        top_k=payload.top_k,
        rerank_n=payload.rerank_n,
        alpha=payload.alpha,
        filters=filter_dicts,
        filter_op=payload.filter_op,
    )
    return result
