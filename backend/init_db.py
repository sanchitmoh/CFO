"""Initialize database schema via Alembic migrations (L-003)."""
import asyncio
from database import engine


async def init_db():
    """Run all Alembic migrations to bring the schema up to date."""
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command

    alembic_cfg = AlembicConfig("alembic.ini")
    async with engine.begin() as conn:
        # Enable pgvector extension first (required before migration tables)
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        await conn.run_sync(
            lambda sync_conn: alembic_command.upgrade(alembic_cfg, "head")
        )

    print("✅ Database initialized successfully via Alembic migrations!")


if __name__ == "__main__":
    asyncio.run(init_db())
