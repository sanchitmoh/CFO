"""
AI CFO — Upstash Redis Cache Layer
Async Redis with JSON serialization for dashboard summaries, forecasts, etc.

SEC-004: Uses per-workspace key tracking sets for efficient bulk deletion.
PERF-002: Adds versioned cache keys — cache invalidation increments a version
counter instead of scanning/deleting keys. Old entries expire naturally via TTL.
"""
import json
import hashlib
import logging
from typing import Any, Optional

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)

_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create a shared async Redis connection.

    PERF-005: Module-level singleton — redis.from_url returns a client backed
    by an internal connection pool. Created once, reused for all callers.
    """
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    return _pool


# ═══════════════════════════════════════════════════════════════════
# PERF-002: Versioned cache keys
# ═══════════════════════════════════════════════════════════════════

async def _get_version(r: redis.Redis, workspace_id: str) -> str:
    """Get the current cache version for a workspace."""
    version = await r.get(f"cache_version:{workspace_id}")
    return version or "0"


async def invalidate_workspace_cache(workspace_id: str) -> None:
    """Invalidate all cached data for a workspace by bumping the version.

    PERF-002: O(1) operation — no scanning, no key deletion.
    Old cache entries expire naturally via TTL.
    """
    try:
        r = await get_redis()
        await r.incr(f"cache_version:{workspace_id}")
    except Exception:
        pass  # Cache failures are non-fatal


def _tracking_key(workspace_id: str) -> str:
    """Return the Redis Set key that tracks all cache keys for a workspace."""
    return f"ws:{workspace_id}:_keys"


# ═══════════════════════════════════════════════════════════════════
# Core cache operations
# ═══════════════════════════════════════════════════════════════════

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
    """Set a cached value with optional TTL (seconds).

    Also registers the key in a per-workspace tracking set for efficient
    bulk deletion (SEC-004).
    """
    try:
        r = await get_redis()
        serialized = json.dumps(value, default=str)
        effective_ttl = ttl or settings.CACHE_TTL_SECONDS
        await r.setex(key, effective_ttl, serialized)

        # SEC-004: Track this key in the workspace's key set
        # Extract workspace_id from key format "ws:{id}:..."
        parts = key.split(":")
        if len(parts) >= 2 and parts[0] == "ws":
            tracking = _tracking_key(parts[1])
            await r.sadd(tracking, key)
            # Keep tracking set alive as long as any cache key could exist
            await r.expire(tracking, effective_ttl * 2)
    except Exception:
        pass  # Cache failures are non-fatal


async def cache_delete(pattern: str) -> None:
    """Delete all cached keys for a workspace pattern.

    SEC-004: Uses the per-workspace tracking set for O(M) deletion
    instead of O(N) scan_iter across the full keyspace.

    Falls back to scan_iter with COUNT hint if tracking set is empty
    (e.g., keys created before the tracking migration).
    """
    try:
        r = await get_redis()

        # Extract workspace_id from pattern "ws:{id}:*" or "ws:{id}:dashboard:*"
        parts = pattern.rstrip("*").rstrip(":").split(":")
        ws_id = parts[1] if len(parts) >= 2 and parts[0] == "ws" else None

        keys_to_delete: list[str] = []

        if ws_id:
            tracking = _tracking_key(ws_id)
            tracked_keys = await r.smembers(tracking)

            if tracked_keys:
                # Filter by pattern prefix (e.g., "ws:{id}:dashboard:")
                prefix = pattern.rstrip("*")
                keys_to_delete = [
                    k for k in tracked_keys
                    if k.startswith(prefix) or pattern.endswith("*") and k.startswith(prefix)
                ]

                if keys_to_delete:
                    await r.delete(*keys_to_delete)
                    # Remove deleted keys from tracking set
                    await r.srem(tracking, *keys_to_delete)
                return

        # Fallback: scan_iter with COUNT hint for pre-migration keys
        logger.debug("cache_delete falling back to scan_iter for pattern: %s", pattern)
        async for key in r.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)
        if keys_to_delete:
            await r.delete(*keys_to_delete)
    except Exception:
        pass


def make_cache_key(prefix: str, workspace_id: str, *parts: str) -> str:
    """Build a consistent cache key: ws:{id}:{prefix}:{parts}"""
    key = f"ws:{workspace_id}:{prefix}"
    if parts:
        key += ":" + ":".join(parts)
    return key


async def make_versioned_cache_key(prefix: str, workspace_id: str, *parts: str) -> str:
    """Build a versioned cache key that auto-invalidates on version bump.

    PERF-002: Key format includes the workspace cache version so that
    after invalidate_workspace_cache(), all new lookups miss automatically.
    Old versioned entries expire naturally via TTL — no scan/delete needed.
    """
    try:
        r = await get_redis()
        version = await _get_version(r, workspace_id)
    except Exception:
        version = "0"

    key = f"ws:{workspace_id}:v{version}:{prefix}"
    if parts:
        key += ":" + ":".join(parts)
    return key


def compute_data_hash(data: list[dict]) -> str:
    """Compute a SHA-256 hash of data for cache invalidation."""
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()
