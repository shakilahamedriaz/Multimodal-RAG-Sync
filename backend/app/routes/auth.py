import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_api_key
from app.database import get_db
from app.models import APIKey

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str
    owner_id: str = "default"


class CreateKeyResponse(BaseModel):
    key: str          # shown ONCE — not stored in DB
    id: uuid.UUID
    name: str
    key_prefix: str
    message: str = "Store this key securely — it will NOT be shown again."


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    owner_id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/keys", response_model=CreateKeyResponse, status_code=201)
async def create_api_key(
    payload: CreateKeyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The full key is returned exactly once — store it immediately."""
    full_key, lookup, key_hash = generate_api_key()
    record = APIKey(
        owner_id=payload.owner_id,
        name=payload.name,
        key_prefix=lookup,
        key_hash=key_hash,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return CreateKeyResponse(
        key=full_key,
        id=record.id,
        name=record.name,
        key_prefix=lookup,
    )


@router.get("/keys", response_model=list[APIKeyResponse])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    """List all active API keys (prefixes only — hashes are never exposed)."""
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True).order_by(APIKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Revoke an API key — it will no longer authenticate."""
    record = await db.get(APIKey, key_id)
    if not record:
        raise HTTPException(status_code=404, detail="API key not found")
    record.is_active = False
    await db.commit()
