"""
AI CFO — Database Configuration
Async SQLAlchemy engine + session factory for Neon PostgreSQL.

EXT-004: Neon URL workaround lives in config.py (Settings.database_url_for_asyncpg).
"""
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text
from config import settings


engine = create_async_engine(
    settings.database_url_for_asyncpg,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=settings.database_connect_args,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_with_rls(workspace_id: str):
    """Yield a DB session with app.workspace_id set for PostgreSQL RLS.

    Usage (in a router with authenticated user):
        db = Depends(lambda: get_db_with_rls(user.workspace_id))

    Or use the dependency helper `get_rls_db` below.
    """
    async with AsyncSessionLocal() as session:
        # SEC-FIX: SET LOCAL doesn't support bind parameters in PostgreSQL
        # We validate the UUID format first to ensure it's safe to interpolate
        import uuid
        workspace_id_str = str(workspace_id)
        uuid.UUID(workspace_id_str)  # Validate UUID format (raises ValueError if invalid)
        await session.execute(
            text(f"SET LOCAL app.workspace_id = '{workspace_id_str}'")
        )
        yield session


@asynccontextmanager
async def get_db_context():
    """Standalone async context manager for background tasks / non-DI usage."""
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_rls_db_context(workspace_id: str):
    """RLS-enabled async context manager for background tasks.

    CRIT-002/CRIT-003/HIGH-003: Background tasks spawned from request
    handlers lose RLS context when they use ``get_db_context()``.  This
    helper creates a session with ``app.workspace_id`` set so that
    PostgreSQL Row-Level Security policies are enforced.

    Usage::

        async with get_rls_db_context(str(workspace_id)) as db:
            await run_alert_engine(db, workspace_id)
    """
    import uuid
    workspace_id_str = str(workspace_id)
    uuid.UUID(workspace_id_str)  # Validate UUID format (raises ValueError if invalid)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(f"SET LOCAL app.workspace_id = '{workspace_id_str}'")
        )
        yield session


async def get_rls_db(user=None):
    """FastAPI dependency: yields a DB session with RLS workspace isolation.

    Usage in routers:
        from database import get_rls_db
        from auth import get_current_user
        from models import User

        @router.get("/")
        async def my_endpoint(
            user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_rls_db),
        ):
            ...

    Note: This depends on `get_current_user` being called first in the
    same request. FastAPI evaluates dependencies lazily, so `user` may
    not be resolved yet. For Phase 1, we use a factory pattern instead.
    """
    # This implementation is used via get_rls_session() below
    pass


def get_rls_session(user):
    """Factory that returns an RLS-enabled DB dependency for a specific user.

    Usage:
        @router.get("/")
        async def endpoint(user: User = Depends(get_current_user)):
            async for db in get_db_with_rls(str(user.workspace_id)):
                ...
    """
    return get_db_with_rls(str(user.workspace_id))


