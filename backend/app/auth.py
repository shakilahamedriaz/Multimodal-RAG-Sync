import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

_bearer = HTTPBearer(auto_error=False)
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

_KEY_PREFIX = "rag_"
_LOOKUP_LEN = 16   # "rag_" (4) + 12 hex chars = enough entropy for O(1) lookup


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        full_key  — shown once to the user, never stored in plaintext
        lookup    — first 16 chars, stored in DB for fast lookup
        key_hash  — bcrypt hash, used to verify the full_key on auth
    """
    token = secrets.token_hex(32)        # 64 hex chars
    full_key = _KEY_PREFIX + token       # "rag_" + 64 chars = 68 chars total
    lookup = full_key[:_LOOKUP_LEN]      # "rag_" + 12 chars
    return full_key, lookup, _pwd.hash(full_key)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency — verifies Bearer token against hashed keys in DB.

    Returns the APIKey record (or None if AUTH_ENABLED=false).
    Raises HTTP 401 on invalid/missing key when auth is enabled.
    """
    from app.config import settings
    from app.models import APIKey

    if not settings.auth_enabled:
        return None   # dev mode: auth disabled

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    lookup = token[:_LOOKUP_LEN]

    result = await db.execute(
        select(APIKey).where(APIKey.key_prefix == lookup, APIKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()

    if api_key is None or not _pwd.verify(token, api_key.key_hash):
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    # Update last_used_at non-blockingly
    api_key.last_used_at = datetime.utcnow()
    await db.commit()

    return api_key
