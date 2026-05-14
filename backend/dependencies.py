"""
AI CFO — Shared FastAPI Dependencies
SEC-002: Provides get_rls_db — the ONLY way to get a DB session in routers.

This module breaks the circular import chain:
  auth.py → database.py (for get_db used during JWT verification)
  dependencies.py → auth.py + database.py (for RLS session creation)
  routers → dependencies.py (for get_rls_db)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Depends

from database import AsyncSessionLocal
from auth import get_current_user
from models import User


async def get_rls_db(user: User = Depends(get_current_user)):
    """FastAPI dependency: yields a DB session with RLS workspace isolation.

    Automatically resolves the current user and sets the PostgreSQL
    ``app.workspace_id`` session variable so that Row-Level Security
    policies filter data to the authenticated user's workspace.

    Usage in routers::

        from dependencies import get_rls_db

        @router.get("/")
        async def my_endpoint(
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_rls_db),
        ):
            ...

    Note: FastAPI caches dependencies per-request, so ``get_current_user``
    is resolved only once even when used both explicitly and inside
    ``get_rls_db``.
    """
    async with AsyncSessionLocal() as session:
        # Ensure an active transaction before SET LOCAL so the RLS variable
        # persists through all queries in this request.  We call begin()
        # without a context-manager so handlers can call db.commit()
        # themselves without prematurely closing the transaction scope.
        if not session.in_transaction():
            await session.begin()
        # SEC-FIX: SET LOCAL doesn't support bind parameters in PostgreSQL
        # We validate the UUID format first to ensure it's safe to interpolate
        workspace_id_str = str(user.workspace_id)
        # Validate UUID format (raises ValueError if invalid)
        import uuid
        uuid.UUID(workspace_id_str)  # This ensures it's a valid UUID
        await session.execute(
            text(f"SET LOCAL app.workspace_id = '{workspace_id_str}'")
        )
        try:
            yield session
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        else:
            if session.in_transaction():
                await session.commit()


def get_forecast_service():
    """EXT-001 + L-004: Dependency that returns the active ForecastService.

    Controlled by ``FORECAST_MODEL`` env var (default: ``"linear"``).

    Supported values:
      - ``"linear"``  → LinearForecastService  (zero extra deps)
      - ``"prophet"`` → ProphetForecastService  (requires ``pip install prophet``)

    No router code needs to change when swapping models.
    """
    from config import settings

    if settings.FORECAST_MODEL == "prophet":
        from services.prophet_forecast_service import ProphetForecastService
        return ProphetForecastService()

    # Default: linear regression
    from services.forecast_service import LinearForecastService
    return LinearForecastService()
