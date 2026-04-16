"""
AI CFO — Upstash Redis Cache Layer
Async Redis with JSON serialization for dashboard summaries, forecasts, etc.
"""
import json
import hashlib
from typing import Any, Optional

import redis.asyncio as redis

from config import settings

_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create a shared async Redis connection."""
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    return _pool


async def cache_get(key: str) -> Optional[Any]:
    """Get a cached value, returns None on miss or error."""
    try:
        r = await get_redis()
        val = await r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception:
        pass  # Cache failures are non-fatal
    return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Set a cached value with optional TTL (seconds)."""
    try:
        r = await get_redis()
        serialized = json.dumps(value, default=str)
        if ttl:
            await r.setex(key, ttl, serialized)
        else:
            await r.setex(key, settings.CACHE_TTL_SECONDS, serialized)
    except Exception:
        pass  # Cache failures are non-fatal


async def cache_delete(pattern: str) -> None:
    """Delete all keys matching a pattern (e.g., 'ws:{id}:*')."""
    try:
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass


def make_cache_key(prefix: str, workspace_id: str, *parts: str) -> str:
    """Build a consistent cache key: ws:{id}:{prefix}:{parts}"""
    key = f"ws:{workspace_id}:{prefix}"
    if parts:
        key += ":" + ":".join(parts)
    return key


def compute_data_hash(data: list[dict]) -> str:
    """Compute a SHA-256 hash of data for cache invalidation."""
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()
