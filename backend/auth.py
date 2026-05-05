"""
AI CFO — Clerk JWT Authentication
Validates Clerk-issued JWTs using JWKS. No custom passwords.

Security hardening:
- Algorithm pinned to RS256 (prevents algorithm confusion attacks)
- JWKS cache with TTL (prevents stale-key + availability issues)
- SEC-001: Redis-backed distributed rate limiting (works across workers/deploys)
- SEC-006: Advisory-lock provisioning (prevents duplicate workspace race)
"""
import time
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import httpx
from jose import jwt, JWTError

from config import settings
from database import get_db
from models import User, Workspace, UserRole
from cache import get_redis

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# ── JWKS cache with TTL ──────────────────────────────────────────
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_jwks_last_failure: float = 0.0  # MED-001: negative-cache sentinel
_jwks_lock = asyncio.Lock()

# Cache JWKS for 5 minutes — balances key-rotation speed vs. availability
JWKS_CACHE_TTL_SECONDS = 300

# MED-001: Cache fetch failures for 30s to avoid hammering Clerk during outages.
# Without this, every request retries the failing HTTP call (2-5s latency each).
JWKS_NEGATIVE_CACHE_TTL_SECONDS = 30


async def _get_jwks(force_refresh: bool = False) -> dict:
    """
    Fetch and cache Clerk's JWKS keys with a TTL.

    - Caches for JWKS_CACHE_TTL_SECONDS (default: 5 min)
    - Uses an async lock to prevent thundering-herd on cold-start
    - force_refresh=True bypasses TTL (used on kid-mismatch rotation)

    If Clerk's JWKS endpoint is down, stale cache is returned as fallback
    for up to 10× the TTL window (50 min) before raising.

    MED-001: Negative caching — failed fetches are cached for 30s so
    subsequent requests use stale cache immediately without re-attempting.
    """
    global _jwks_cache, _jwks_fetched_at, _jwks_last_failure

    now = time.monotonic()
    cache_age = now - _jwks_fetched_at

    # Return cached if within TTL and not forcing refresh
    if (
        _jwks_cache is not None
        and not force_refresh
        and cache_age < JWKS_CACHE_TTL_SECONDS
    ):
        return _jwks_cache

    async with _jwks_lock:
        # Double-check after acquiring lock (another coroutine may have refreshed)
        now = time.monotonic()
        cache_age = now - _jwks_fetched_at
        if (
            _jwks_cache is not None
            and not force_refresh
            and cache_age < JWKS_CACHE_TTL_SECONDS
        ):
            return _jwks_cache

        # MED-001: If we recently failed, don't retry — return stale or raise.
        # This prevents every request from adding 2-5s latency during a Clerk outage.
        failure_age = now - _jwks_last_failure
        if _jwks_last_failure > 0 and failure_age < JWKS_NEGATIVE_CACHE_TTL_SECONDS:
            if _jwks_cache is not None:
                logger.debug(
                    "JWKS negative cache active (%.0fs ago) — returning stale keys",
                    failure_age,
                )
                return _jwks_cache
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    settings.CLERK_JWKS_URL,
                    headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                )
                resp.raise_for_status()
                _jwks_cache = resp.json()
                _jwks_fetched_at = time.monotonic()
                _jwks_last_failure = 0.0  # Clear negative cache on success
                return _jwks_cache

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            # MED-001: Record the failure timestamp for negative caching
            _jwks_last_failure = time.monotonic()
            logger.warning(
                "JWKS fetch failed — negative-cached for %ds: %s",
                JWKS_NEGATIVE_CACHE_TTL_SECONDS,
                exc,
            )

            # If we have stale cache within 10× TTL, use it (graceful degradation)
            if _jwks_cache is not None and cache_age < JWKS_CACHE_TTL_SECONDS * 10:
                return _jwks_cache
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            ) from exc


def _find_key(jwks: dict, kid: str) -> dict | None:
    """Find the matching key in JWKS by key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


# ── SEC-001: Redis-backed rate limiter for failed auth attempts ───
# Uses Redis sorted sets with timestamps as scores for a sliding window.
# Works across all workers/processes and survives deploys.
# SEC-FIX: Strengthened rate limiting with exponential backoff
AUTH_RATE_LIMIT_WINDOW = 60      # seconds
AUTH_RATE_LIMIT_MAX_FAILURES = 5  # max failures per IP per window (reduced from 10)
AUTH_RATE_LIMIT_LOCKOUT_DURATION = 900  # 15 minutes lockout after exceeding limit


async def _check_rate_limit(client_ip: str) -> None:
    """
    Block IPs that have exceeded the failure threshold within the window.
    Uses Redis sorted set for distributed rate limiting.
    Gracefully degrades (skips check) if Redis is unavailable.
    
    SEC-FIX: Added lockout mechanism for repeated failures.
    """
    try:
        r = await get_redis()
        
        # Check if IP is in lockout
        lockout_key = f"ratelimit:lockout:{client_ip}"
        is_locked = await r.get(lockout_key)
        if is_locked:
            ttl = await r.ttl(lockout_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily locked due to too many failed attempts. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)},
            )
        
        key = f"ratelimit:auth:{client_ip}"
        now = time.time()
        window_start = now - AUTH_RATE_LIMIT_WINDOW

        # Remove expired entries
        await r.zremrangebyscore(key, "-inf", window_start)

        # Count failures in current window
        failure_count = await r.zcard(key)

        if failure_count >= AUTH_RATE_LIMIT_MAX_FAILURES:
            # Trigger lockout
            await r.setex(lockout_key, AUTH_RATE_LIMIT_LOCKOUT_DURATION, "1")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many authentication failures. Account locked for {AUTH_RATE_LIMIT_LOCKOUT_DURATION // 60} minutes.",
                headers={"Retry-After": str(AUTH_RATE_LIMIT_LOCKOUT_DURATION)},
            )
    except HTTPException:
        raise  # Re-raise our own 429
    except Exception:
        # Redis down — degrade gracefully, don't block auth
        logger.warning("Rate limiter unavailable (Redis down), skipping check")


async def _record_auth_failure(client_ip: str) -> None:
    """Record a failed auth attempt in Redis sorted set."""
    try:
        r = await get_redis()
        key = f"ratelimit:auth:{client_ip}"
        now = time.time()
        # Use timestamp + random suffix as member to avoid dedup
        member = f"{now}:{id(object())}"
        await r.zadd(key, {member: now})
        # Set key TTL so it auto-cleans even without explicit prune
        await r.expire(key, AUTH_RATE_LIMIT_WINDOW * 2)
    except Exception:
        logger.warning("Failed to record auth failure in Redis")


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT and return the decoded payload.
    Raises HTTPException on invalid/expired tokens.

    Security controls:
    - algorithms pinned to ["RS256"] only (no "none", no "HS256")
    - JWKS key matched by kid with automatic rotation fallback
    - issuer verified when configured
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode header to get kid — this does NOT verify the signature
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg")

        if not kid:
            raise credentials_exception

        # Reject tokens that claim a different algorithm than RS256
        # (defense-in-depth against algorithm confusion even though
        #  we also pin algorithms= in decode())
        if alg and alg.upper() != "RS256":
            raise credentials_exception

        # Fetch JWKS and find matching key
        jwks = await _get_jwks()
        key = _find_key(jwks, kid)
        if not key:
            # Key might have rotated — force-refresh JWKS cache
            jwks = await _get_jwks(force_refresh=True)
            key = _find_key(jwks, kid)
            if not key:
                raise credentials_exception

        # Verify and decode the JWT
        # CRITICAL: algorithms MUST be pinned to ["RS256"] to prevent
        # algorithm-confusion attacks where an attacker uses "none" or
        # "HS256" with the RSA public key as the HMAC secret.
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't always set aud
                "verify_iss": bool(settings.CLERK_ISSUER),
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "sub", "iat"],
            },
            issuer=settings.CLERK_ISSUER or None,
        )
        return payload

    except JWTError:
        raise credentials_exception


async def _extract_clerk_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, dict]:
    """
    Verify the JWT and return (clerk_id, full_payload).
    Handles rate limiting and raises 401 on failures.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit BEFORE doing any work (now async/Redis-backed)
    await _check_rate_limit(client_ip)

    if credentials is None:
        await _record_auth_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = await verify_clerk_token(credentials.credentials)
    except HTTPException:
        await _record_auth_failure(client_ip)
        raise

    clerk_id = payload.get("sub")
    if not clerk_id:
        await _record_auth_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    return clerk_id, payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Pure authentication dependency — verifies the Clerk JWT and looks up
    the existing user.  Does NOT create workspaces or users.

    Raises 401 if the token is invalid or the user hasn't been provisioned yet.
    """
    clerk_id, _payload = await _extract_clerk_id(request, credentials)

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not provisioned. Call POST /api/onboarding/provision first.",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def provision_user_and_workspace(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, bool]:
    """
    Provision dependency — creates workspace + user on first call,
    returns existing user on subsequent calls (idempotent).

    SEC-006: Uses PostgreSQL advisory lock keyed on clerk_id to serialize
    concurrent first-login attempts, preventing orphaned workspaces.

    Returns (user, was_created) so callers know if this was a new provision.
    Used ONLY by the onboarding/provision endpoint.
    """
    clerk_id, payload = await _extract_clerk_id(request, credentials)

    # Fast path — check if user already exists (no lock needed)
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is not None:
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        return user, False

    # SEC-006: Acquire advisory lock to serialize provisioning for this clerk_id.
    # This prevents two simultaneous SSO redirects from both creating workspaces.
    # The lock is automatically released when the transaction commits/rollbacks.
    lock_key = int(hashlib.sha256(clerk_id.encode()).hexdigest()[:15], 16)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

    # Re-check after acquiring lock (another request may have provisioned)
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is not None:
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        return user, False

    # First-time provisioning — create workspace + user (now serialized)
    email = payload.get("email", payload.get("email_addresses", [{}])[0].get("email_address", ""))
    full_name = payload.get("name", payload.get("first_name", "User"))
    if isinstance(full_name, dict):
        full_name = f"{full_name.get('first_name', '')} {full_name.get('last_name', '')}".strip()

    workspace = Workspace(name=f"{full_name}'s Workspace")
    db.add(workspace)
    await db.flush()

    user = User(
        clerk_id=clerk_id,
        workspace_id=workspace.id,
        email=email or f"{clerk_id}@clerk.user",
        full_name=full_name or "User",
        role=UserRole.owner,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user, True
