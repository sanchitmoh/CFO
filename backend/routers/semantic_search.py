"""
AI CFO — Semantic Search Router (ADVANCE-005)
Natural-language search over transactions using pgvector embeddings.
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_db_context
from auth import get_current_user
from models import User
from services.embedding_service import (
    get_relevant_transactions,
    batch_embed_transactions,
)

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SemanticSearchResult(BaseModel):
    id: uuid.UUID
    description: str
    amount: float
    category: str
    type: str
    date: str
    vendor: str | None = None
    similarity: float


@router.post("/semantic", response_model=list[SemanticSearchResult])
async def semantic_search(
    data: SemanticSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search transactions using natural language.

    Examples:
      - "Find all subscriptions I forgot about"
      - "Restaurant expenses last month"
      - "Large software purchases"
      - "Recurring office supplies"

    Uses pgvector cosine similarity with all-MiniLM-L6-v2 embeddings (free).
    """
    results = await get_relevant_transactions(
        db, user.workspace_id, data.query, top_k=min(data.top_k, 50)
    )

    return [
        SemanticSearchResult(
            id=row.id,
            description=row.description,
            amount=float(row.amount),
            category=row.category,
            type=row.type,
            date=row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
            vendor=row.vendor,
            similarity=round(float(row.similarity), 4),
        )
        for row in results
    ]


@router.post("/backfill-embeddings")
async def backfill_embeddings(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a background job to embed all un-embedded transactions.

    This is a manual trigger for the workspace admin to backfill
    embeddings for existing transactions.
    """
    async def _backfill():
        async with get_db_context() as bg_db:
            count = await batch_embed_transactions(user.workspace_id, bg_db)
            return count

    background_tasks.add_task(_backfill)
    return {
        "status": "backfill_started",
        "message": "Embedding generation started in background for your workspace.",
    }
