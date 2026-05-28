import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Ingestion DTOs (Phase 2) ──────────────────────────────────────────────────

@dataclass
class ParsedPage:
    page_number: int         # 1-indexed
    text: str
    chunk_type: str = "text" # "text" | "table" | "image_caption" — carried to TextChunk


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    page_count: int
    mime_type: str


@dataclass
class TextChunk:
    text: str
    token_count: int
    page_number: int
    chunk_index: int
    chunk_type: str = "text"
    chunk_metadata: dict = field(default_factory=dict)


# ── Retrieval DTOs (Phase 3) ──────────────────────────────────────────────────

@dataclass
class ChunkResult:
    """A retrieved chunk with all scores attached. Flows through retrieve → rerank → generate."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    kb_id: uuid.UUID
    chunk_text: str
    chunk_type: str
    page_number: Optional[int]
    chunk_index: int
    token_count: int
    embedding_model: str
    filename: str
    dense_score: float
    sparse_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: Optional[float] = None


class SourceCitation(BaseModel):
    """Serialisable source attribution returned to the API caller."""
    source_index: int
    chunk_id: str
    document_id: str
    filename: str
    page_number: Optional[int]
    excerpt: str
    similarity_score: float
    rerank_score: Optional[float] = None


# ── Chat DTOs ─────────────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    stream: bool = True


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[list[SourceCitation]] = None
    has_answer: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageOut] = []

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class ConversationRenameIn(BaseModel):
    title: str
