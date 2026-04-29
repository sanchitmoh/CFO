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
        # SEC-FIX: Use parameterized query to prevent SQL injection
        await session.execute(
            text("SET LOCAL app.workspace_id = :ws_id"),
            {"ws_id": str(workspace_id)}
        )
        yield session


@asynccontextmanager
async def get_db_context():
    """Standalone async context manager for background tasks / non-DI usage."""
    async with AsyncSessionLocal() as session:
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


