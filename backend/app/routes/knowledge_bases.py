import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import KnowledgeBase, Document

router = APIRouter(prefix="/kb", tags=["knowledge-bases"])


class KBCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: str = Field("text-embedding-3-small")
    llm_model: str = Field("gpt-4o")
    chunking_strategy: str = Field("recursive")
    chunk_size: int = Field(512, ge=128, le=2048)
    chunk_overlap: int = Field(64, ge=0, le=256)
    similarity_threshold: float = Field(0.35, ge=0.0, le=1.0)


class KBUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    llm_model: Optional[str] = None
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class KBResponse(BaseModel):
    id: UUID
    owner_id: str
    name: str
    description: Optional[str]
    embedding_model: str
    llm_model: str
    chunking_strategy: str
    chunk_size: int
    chunk_overlap: int
    similarity_threshold: float
    document_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


async def _get_kb_or_404(kb_id: UUID, db: AsyncSession) -> KnowledgeBase:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


async def _doc_count(kb_id: UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Document.id)).where(Document.kb_id == kb_id)
    )
    return result.scalar_one()


@router.post("", response_model=KBResponse, status_code=201)
async def create_kb(payload: KBCreate, db: AsyncSession = Depends(get_db)):
    kb = KnowledgeBase(owner_id="default", **payload.model_dump())
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return {**kb.__dict__, "document_count": 0}


@router.get("", response_model=list[KBResponse])
async def list_kbs(db: AsyncSession = Depends(get_db)):
    count_sub = (
        select(func.count(Document.id))
        .where(Document.kb_id == KnowledgeBase.id)
        .scalar_subquery()
    )
    result = await db.execute(
        select(KnowledgeBase, count_sub.label("document_count"))
        .order_by(KnowledgeBase.created_at.desc())
    )
    return [
        {**kb.__dict__, "document_count": doc_count}
        for kb, doc_count in result.all()
    ]


@router.get("/{kb_id}", response_model=KBResponse)
async def get_kb(kb_id: UUID, db: AsyncSession = Depends(get_db)):
    kb = await _get_kb_or_404(kb_id, db)
    return {**kb.__dict__, "document_count": await _doc_count(kb_id, db)}


@router.patch("/{kb_id}", response_model=KBResponse)
async def update_kb(kb_id: UUID, payload: KBUpdate, db: AsyncSession = Depends(get_db)):
    kb = await _get_kb_or_404(kb_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(kb, field, value)
    kb.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(kb)
    return {**kb.__dict__, "document_count": await _doc_count(kb_id, db)}


@router.delete("/{kb_id}", status_code=204)
async def delete_kb(kb_id: UUID, db: AsyncSession = Depends(get_db)):
    kb = await _get_kb_or_404(kb_id, db)
    await db.delete(kb)
    await db.commit()
