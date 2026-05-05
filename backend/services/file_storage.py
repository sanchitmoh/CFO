"""
AI CFO — File Storage Service (FILE-001)
Handles saving, retrieving, and hashing uploaded files.
Pluggable: swap local storage for S3/R2/GCS by changing STORAGE_BACKEND env var.

SEC-FIX: Enhanced with path traversal protection and filename sanitization.
INFRA-001: Abstraction layer supports local and cloud storage backends.
"""
import hashlib
import uuid
import re
import os
from pathlib import Path
from typing import Protocol

import aiofiles
import aiofiles.os

from config import settings

# SEC-FIX: Filename sanitization
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")
MAX_FILENAME_LENGTH = 255


# ═══════════════════════════════════════════════════════════════════
# INFRA-001: Storage Backend Protocol
# ═══════════════════════════════════════════════════════════════════

class StorageBackend(Protocol):
    """Protocol for pluggable storage backends.
    
    INFRA-001: Allows swapping between local disk, S3, R2, GCS without
    changing router code. Implementations must be async.
    """
    
    async def save(
        self,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Save file and return storage path/key."""
        ...
    
    async def get(self, storage_path: str) -> bytes:
        """Retrieve file content by storage path/key."""
        ...
    
    async def delete(self, storage_path: str) -> None:
        """Delete file by storage path/key."""
        ...


class LocalStorageBackend:
    """Local filesystem storage backend.
    
    INFRA-001: Default implementation for development and single-server deployments.
    For production multi-pod deployments, use S3StorageBackend instead.
    """
    
    def __init__(self, base_dir: str | None = None):
        """Initialize with base directory (defaults to settings.UPLOAD_DIR)."""
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
    
    async def save(
        self,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Persist file to local disk.
        
        Directory structure: {base_dir}/{workspace_id}/{file_uuid}/{filename}
        Returns relative path from base_dir.
        """
        safe_filename = sanitize_filename(filename)
        file_uuid = uuid.uuid4()
        rel_path = f"{workspace_id}/{file_uuid}/{safe_filename}"
        full_path = self.base_dir / str(workspace_id) / str(file_uuid)

        await aiofiles.os.makedirs(str(full_path), exist_ok=True)

        file_path = full_path / safe_filename
        async with aiofiles.open(str(file_path), "wb") as f:
            await f.write(content)

        return rel_path
    
    async def get(self, storage_path: str) -> bytes:
        """Read file from local disk.
        
        SEC-FIX: Validates path to prevent directory traversal attacks.
        """
        full_path = (self.base_dir / storage_path).resolve()
        
        # SEC-FIX: Ensure the resolved path is within the base directory
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid storage path: path traversal detected")
        
        if not full_path.exists():
            raise FileNotFoundError(f"Upload not found: {storage_path}")
        
        async with aiofiles.open(str(full_path), "rb") as f:
            return await f.read()
    
    async def delete(self, storage_path: str) -> None:
        """Delete file from local disk."""
        full_path = (self.base_dir / storage_path).resolve()
        
        # SEC-FIX: Ensure the resolved path is within the base directory
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid storage path: path traversal detected")
        
        if full_path.exists():
            await aiofiles.os.remove(str(full_path))


class S3StorageBackend:
    """S3-compatible storage backend (AWS S3, Cloudflare R2, MinIO, etc.).
    
    INFRA-001: Production-ready backend for horizontal scaling.
    Supports pre-signed URLs for direct client uploads/downloads.
    
    To enable:
        1. Set STORAGE_BACKEND=s3 in .env
        2. Configure AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        3. Set S3_BUCKET_NAME and optionally S3_REGION, S3_ENDPOINT_URL
    
    For Cloudflare R2:
        - Set S3_ENDPOINT_URL to your R2 endpoint
        - Use R2 access keys
    """
    
    def __init__(
        self,
        bucket_name: str | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
    ):
        """Initialize S3 backend with bucket configuration."""
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "ai-cfo-uploads")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self._client = None
    
    async def _get_client(self):
        """Lazy-load boto3 client (only imported if S3 backend is used)."""
        if self._client is None:
            try:
                import aioboto3
                session = aioboto3.Session()
                self._client = await session.client(
                    's3',
                    region_name=self.region,
                    endpoint_url=self.endpoint_url,
                ).__aenter__()
            except ImportError:
                raise RuntimeError(
                    "S3 storage backend requires aioboto3. "
                    "Install with: pip install aioboto3"
                )
        return self._client
    
    async def save(
        self,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        """Upload file to S3 and return S3 key."""
        safe_filename = sanitize_filename(filename)
        file_uuid = uuid.uuid4()
        s3_key = f"{workspace_id}/{file_uuid}/{safe_filename}"
        
        client = await self._get_client()
        await client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=content,
            ContentType="text/csv",  # Adjust based on file type
        )
        
        return s3_key
    
    async def get(self, storage_path: str) -> bytes:
        """Download file from S3."""
        client = await self._get_client()
        response = await client.get_object(
            Bucket=self.bucket_name,
            Key=storage_path,
        )
        return await response['Body'].read()
    
    async def delete(self, storage_path: str) -> None:
        """Delete file from S3."""
        client = await self._get_client()
        await client.delete_object(
            Bucket=self.bucket_name,
            Key=storage_path,
        )
    
    async def generate_presigned_url(
        self,
        storage_path: str,
        expiration: int = 3600,
    ) -> str:
        """Generate pre-signed URL for direct client access.
        
        INFRA-001: Allows clients to download files directly from S3
        without proxying through the backend server.
        """
        client = await self._get_client()
        return await client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': storage_path,
            },
            ExpiresIn=expiration,
        )


# ═══════════════════════════════════════════════════════════════════
# Storage Backend Factory
# ═══════════════════════════════════════════════════════════════════

def get_storage_backend() -> StorageBackend:
    """Factory function to get the configured storage backend.
    
    INFRA-001: Controlled by STORAGE_BACKEND env var (default: "local").
    
    Supported values:
      - "local"  → LocalStorageBackend (default, single-server)
      - "s3"     → S3StorageBackend (production, horizontal scaling)
    
    No router code needs to change when swapping backends.
    """
    backend_type = os.getenv("STORAGE_BACKEND", "local").lower()
    
    if backend_type == "s3":
        return S3StorageBackend()
    
    # Default: local filesystem
    return LocalStorageBackend()


# Global storage backend instance
_storage_backend: StorageBackend = get_storage_backend()


# ═══════════════════════════════════════════════════════════════════
# Public API (unchanged interface for backward compatibility)
# ═══════════════════════════════════════════════════════════════════


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
    """Persist the original uploaded file using the configured storage backend.

    Returns the storage path/key (used as the DB reference).
    
    INFRA-001: Automatically uses local or S3 storage based on STORAGE_BACKEND env var.
    SEC-FIX: Sanitizes filename to prevent path traversal attacks.
    """
    return await _storage_backend.save(workspace_id, filename, content)


async def get_upload(storage_path: str) -> bytes:
    """Read a previously stored upload using the configured storage backend.
    
    INFRA-001: Automatically uses local or S3 storage based on STORAGE_BACKEND env var.
    SEC-FIX: Validates path to prevent directory traversal attacks (in backend implementation).
    """
    return await _storage_backend.get(storage_path)


async def delete_upload(storage_path: str) -> None:
    """Delete a stored upload using the configured storage backend.
    
    INFRA-001: Automatically uses local or S3 storage based on STORAGE_BACKEND env var.
    """
    return await _storage_backend.delete(storage_path)
