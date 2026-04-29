"""
AI CFO — File Storage Service (FILE-001)
Handles saving, retrieving, and hashing uploaded files.
Pluggable: swap local storage for S3 by changing save_upload / get_upload.

SEC-FIX: Enhanced with path traversal protection and filename sanitization.
"""
import hashlib
import uuid
import re
from pathlib import Path

import aiofiles
import aiofiles.os

from config import settings

# SEC-FIX: Filename sanitization
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")
MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks.
    
    SEC-FIX: Removes path separators, null bytes, and other dangerous characters.
    """
    # Remove path components
    filename = Path(filename).name
    
    # Remove null bytes
    filename = filename.replace("\x00", "")
    
    # Replace unsafe characters with underscores
    filename = SAFE_FILENAME_RE.sub("_", filename)
    
    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        # Keep extension if present
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_len = MAX_FILENAME_LENGTH - len(ext) - 1
        filename = name[:max_name_len] + ("." + ext if ext else "")
    
    # Ensure filename is not empty after sanitization
    if not filename or filename in (".", ".."):
        filename = "upload.csv"
    
    return filename


async def compute_content_hash(content: bytes) -> str:
    """SHA-256 hash of file content for duplicate detection."""
    return hashlib.sha256(content).hexdigest()


async def save_upload(
    workspace_id: uuid.UUID,
    filename: str,
    content: bytes,
) -> str:
    """Persist the original uploaded file to disk.

    Returns the relative storage path (used as the DB key).
    Directory structure: {UPLOAD_DIR}/{workspace_id}/{file_uuid}/{filename}
    
    SEC-FIX: Sanitizes filename to prevent path traversal attacks.
    """
    # SEC-FIX: Sanitize filename before using it
    safe_filename = sanitize_filename(filename)
    
    upload_dir = Path(settings.UPLOAD_DIR)
    file_uuid = uuid.uuid4()
    rel_path = f"{workspace_id}/{file_uuid}/{safe_filename}"
    full_path = upload_dir / str(workspace_id) / str(file_uuid)

    await aiofiles.os.makedirs(str(full_path), exist_ok=True)

    file_path = full_path / safe_filename
    async with aiofiles.open(str(file_path), "wb") as f:
        await f.write(content)

    return rel_path


async def get_upload(storage_path: str) -> bytes:
    """Read a previously stored upload from disk.
    
    SEC-FIX: Validates path to prevent directory traversal attacks.
    """
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    full_path = (upload_dir / storage_path).resolve()
    
    # SEC-FIX: Ensure the resolved path is within the upload directory
    if not str(full_path).startswith(str(upload_dir)):
        raise ValueError(f"Invalid storage path: path traversal detected")
    
    if not full_path.exists():
        raise FileNotFoundError(f"Upload not found: {storage_path}")
    
    async with aiofiles.open(str(full_path), "rb") as f:
        return await f.read()
