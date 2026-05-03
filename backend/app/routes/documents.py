import mimetypes
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, DocumentStatus, KnowledgeBase
from app.parsers import SUPPORTED_MIME_TYPES
from app.services.ingestion_service import get_job_status_from_redis, ingest_document
from app.storage import compute_hash, save_file

router = APIRouter(prefix="/kb", tags=["documents"])

_MAX_FILES_PER_UPLOAD = 100
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


# ── Schemas ───────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: UUID
    kb_id: UUID
    filename: str
    mime_type: str
    status: str
    page_count: Optional[int]
    chunk_count: int
    error_message: Optional[str]
    created_at: datetime
    ingested_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    filename: str
    status: str           # "queued" | "duplicate" | "unsupported" | "error"
    document_id: Optional[UUID] = None
    job_id: Optional[str] = None
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    document_id: Optional[UUID]
    status: str
    message: Optional[str]
    updated_at: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_mime(file: UploadFile) -> str:
    if file.content_type and file.content_type != "application/octet-stream":
        return file.content_type
    guessed, _ = mimetypes.guess_type(file.filename or "")
    return guessed or "application/octet-stream"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{kb_id}/documents", response_model=list[UploadResult], status_code=202)
async def upload_documents(
    kb_id: UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> list[UploadResult]:
    """Upload one or more documents (max 100) for async ingestion.
    Returns immediately with a job_id per file; poll /status/{job_id} for progress.
    """
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    if len(files) > _MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=422,
            detail=f"Maximum {_MAX_FILES_PER_UPLOAD} files per request",
        )

    results: list[UploadResult] = []
    queued_doc_ids: list[UUID] = []

    for file in files:
        filename = file.filename or "unknown"
        mime_type = _resolve_mime(file)

        # ── Validate MIME ────────────────────────────────────────────────
        if mime_type not in SUPPORTED_MIME_TYPES:
            results.append(UploadResult(
                filename=filename,
                status="unsupported",
                message=f"MIME type {mime_type!r} not supported. Supported: {sorted(SUPPORTED_MIME_TYPES)}",
            ))
            continue

        # ── Read & validate size ─────────────────────────────────────────
        content = await file.read()
        if len(content) == 0:
            results.append(UploadResult(filename=filename, status="error", message="Empty file"))
            continue
        if len(content) > _MAX_FILE_BYTES:
            results.append(UploadResult(
                filename=filename,
                status="error",
                message=f"File exceeds 50 MB limit ({len(content) // 1_048_576} MB)",
            ))
            continue

        # ── Deduplication by SHA-256 hash ────────────────────────────────
        file_hash = compute_hash(content)
        dup_result = await db.execute(
            select(Document).where(
                Document.kb_id == kb_id,
                Document.file_hash == file_hash,
            )
        )
        if dup_result.scalar_one_or_none():
            results.append(UploadResult(
                filename=filename,
                status="duplicate",
                message="Identical file already exists in this knowledge base",
            ))
            continue

        # ── Save to storage ──────────────────────────────────────────────
        storage_key = await save_file(content, filename)

        # ── Create Document record ───────────────────────────────────────
        doc = Document(
            kb_id=kb_id,
            filename=filename,
            file_hash=file_hash,
            storage_key=storage_key,
            mime_type=mime_type,
            status=DocumentStatus.QUEUED,
        )
        db.add(doc)
        await db.flush()  # materialise doc.id before commit

        queued_doc_ids.append(doc.id)
        results.append(UploadResult(
            filename=filename,
            status="queued",
            document_id=doc.id,
            job_id=str(doc.id),
            message="Document queued for ingestion",
        ))

    # Commit all new Document rows before launching background tasks
    await db.commit()

    for doc_id in queued_doc_ids:
        background_tasks.add_task(ingest_document, doc_id)

    return results


@router.get("/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(kb_id: UUID, db: AsyncSession = Depends(get_db)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    result = await db.execute(
        select(Document)
        .where(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{kb_id}/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    kb_id: UUID,
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Poll ingestion progress. Checks Redis first (fast path), falls back to DB."""
    # ── Fast path: Redis ─────────────────────────────────────────────────
    redis_data = await get_job_status_from_redis(job_id)
    if redis_data:
        try:
            doc_uuid = UUID(job_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid job ID format")
        return JobStatusResponse(
            job_id=job_id,
            document_id=doc_uuid,
            status=redis_data.get("status", "UNKNOWN"),
            message=redis_data.get("message"),
            updated_at=redis_data.get("updated_at"),
        )

    # ── Slow path: DB ────────────────────────────────────────────────────
    try:
        doc_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(Document).where(Document.id == doc_uuid, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        document_id=doc.id,
        status=doc.status,
        message=doc.error_message,
    )


@router.delete("/{kb_id}/documents/{doc_id}", status_code=204)
async def delete_document(kb_id: UUID, doc_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
