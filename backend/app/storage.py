import hashlib
from pathlib import Path

import aiofiles

from app.config import settings


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def save_file(content: bytes, filename: str) -> str:
    """Persist raw bytes to local storage using content-hash naming.
    Returns the storage_key (relative filename within storage root).
    Idempotent: re-uploading the same content is a no-op.
    """
    file_hash = compute_hash(content)
    ext = Path(filename).suffix.lower()
    storage_key = f"{file_hash}{ext}"

    storage_dir = Path(settings.local_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    dest = storage_dir / storage_key
    if not dest.exists():
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)

    return storage_key


async def load_file(storage_key: str) -> bytes:
    """Read raw bytes for a previously saved file."""
    path = Path(settings.local_storage_path) / storage_key
    async with aiofiles.open(path, "rb") as f:
        return await f.read()


async def delete_file(storage_key: str) -> None:
    """Remove a file from local storage (best-effort, ignores missing)."""
    path = Path(settings.local_storage_path) / storage_key
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
