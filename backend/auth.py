"""
AI CFO — Clerk JWT Authentication
Validates Clerk-issued JWTs using JWKS. No custom passwords.

Security hardening (SEC-001):
- Algorithm pinned to RS256 (prevents algorithm confusion attacks)
- JWKS cache with TTL (prevents stale-key + availability issues)
- Rate limiting on failed auth attempts (prevents brute-force/replay)
"""
import time
import asyncio
from datetime import datetime
from collections import defaultdict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from jose import jwt, JWTError

from config import settings
from database import get_db
from models import User, Workspace, UserRole

security = HTTPBearer(auto_error=False)

# ── JWKS cache with TTL ──────────────────────────────────────────
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_jwks_lock = asyncio.Lock()

# Cache JWKS for 5 minutes — balances key-rotation speed vs. availability
JWKS_CACHE_TTL_SECONDS = 300


async def _get_jwks(force_refresh: bool = False) -> dict:
    """
    Fetch and cache Clerk's JWKS keys with a TTL.

    - Caches for JWKS_CACHE_TTL_SECONDS (default: 5 min)
    - Uses an async lock to prevent thundering-herd on cold-start
    - force_refresh=True bypasses TTL (used on kid-mismatch rotation)

    If Clerk's JWKS endpoint is down, stale cache is returned as fallback
    for up to 10× the TTL window (50 min) before raising.
    """
    global _jwks_cache, _jwks_fetched_at

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

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    settings.CLERK_JWKS_URL,
                    headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                )
                resp.raise_for_status()
                _jwks_cache = resp.json()
                _jwks_fetched_at = time.monotonic()
                return _jwks_cache

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
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


# ── Rate limiter for failed auth attempts ─────────────────────────
# Tracks per-IP failure counts with a sliding window.
_auth_failures: dict[str, list[float]] = defaultdict(list)
AUTH_RATE_LIMIT_WINDOW = 60      # seconds
AUTH_RATE_LIMIT_MAX_FAILURES = 10  # max failures per IP per window


def _check_rate_limit(client_ip: str) -> None:
    """
    Block IPs that have exceeded the failure threshold within the window.
    Prevents brute-force and replay attacks against the auth endpoint.
    """
    now = time.monotonic()
    # Prune old entries
    _auth_failures[client_ip] = [
        ts for ts in _auth_failures[client_ip]
        if now - ts < AUTH_RATE_LIMIT_WINDOW
    ]
    if len(_auth_failures[client_ip]) >= AUTH_RATE_LIMIT_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication failures. Try again later.",
            headers={"Retry-After": str(AUTH_RATE_LIMIT_WINDOW)},
        )


def _record_auth_failure(client_ip: str) -> None:
    """Record a failed auth attempt for rate-limit tracking."""
    _auth_failures[client_ip].append(time.monotonic())


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

    # Check rate limit BEFORE doing any work
    _check_rate_limit(client_ip)

    if credentials is None:
        _record_auth_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = await verify_clerk_token(credentials.credentials)
    except HTTPException:
        _record_auth_failure(client_ip)
        raise

    clerk_id = payload.get("sub")
    if not clerk_id:
        _record_auth_failure(client_ip)
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
    user.last_login_at = datetime.utcnow()
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

    Returns (user, was_created) so callers know if this was a new provision.
    Used ONLY by the onboarding/provision endpoint.
    """
    clerk_id, payload = await _extract_clerk_id(request, credentials)

    # Check if user already exists (idempotent)
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is not None:
        user.last_login_at = datetime.utcnow()
        await db.commit()
        return user, False

    # First-time provisioning — create workspace + user
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
