import uuid
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel


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
