"""
AI CFO — Clerk JWT Authentication
Validates Clerk-issued JWTs using JWKS. No custom passwords.
"""
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode

from config import settings
from database import get_db
from models import User, Workspace, UserRole

security = HTTPBearer(auto_error=False)

# ── JWKS cache ────────────────────────────────────────────────────
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS keys."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            settings.CLERK_JWKS_URL,
            headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
        )
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


def _find_key(jwks: dict, kid: str) -> dict | None:
    """Find the matching key in JWKS by key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT and return the decoded payload.
    Raises HTTPException on invalid/expired tokens.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise credentials_exception

        # Fetch JWKS and find matching key
        jwks = await _get_jwks()
        key = _find_key(jwks, kid)
        if not key:
            # Key might have rotated — refetch
            global _jwks_cache
            _jwks_cache = None
            jwks = await _get_jwks()
            key = _find_key(jwks, kid)
            if not key:
                raise credentials_exception

        # Verify and decode the JWT
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't always set aud
                "verify_iss": bool(settings.CLERK_ISSUER),
            },
            issuer=settings.CLERK_ISSUER or None,
        )
        return payload

    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the Clerk JWT, then find or create the user
    in our database. This enables seamless Clerk → local DB user sync.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await verify_clerk_token(credentials.credentials)

    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    # Look up user by clerk_id
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-provision: create workspace + user on first login
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

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user
