"""
AI CFO — Database Configuration
Async SQLAlchemy engine + session factory for Neon PostgreSQL.
"""
import ssl as _ssl
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text
from config import settings


def _fix_neon_url(url: str) -> tuple[str, dict]:
    """
    Neon DSNs contain ?sslmode=require which asyncpg rejects.
    Strip sslmode from the query string and return (clean_url, connect_args).
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    needs_ssl = params.pop("sslmode", [None])[0] in ("require", "verify-full", "verify-ca")

    clean_query = urlencode({k: v[0] for k, v in params.items()}) if params else ""
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args = {}
    if needs_ssl:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return clean_url, connect_args


_clean_url, _connect_args = _fix_neon_url(settings.DATABASE_URL)

engine = create_async_engine(
    _clean_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_connect_args,
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
        await session.execute(
            text("SET LOCAL app.workspace_id = :ws_id"),
            {"ws_id": str(workspace_id)},
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


