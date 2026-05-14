"""
AI CFO — Embedding Service (ADVANCE-005)
Free, local embeddings using sentence-transformers (all-MiniLM-L6-v2).
No API costs — runs entirely on-device.

Provides:
  - generate_embedding(text) → list[float] (384 dims)
  - embed_transaction(txn, db)  — stores embedding for a single transaction
  - batch_embed_transactions(workspace_id, db) — backfill all un-embedded txns
  - get_relevant_transactions(db, ws_id, query, top_k) — semantic search via pgvector
"""
import logging
import asyncio
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from telemetry import traced

logger = logging.getLogger(__name__)

# ── Lazy-loaded model singleton ───────────────────────────────────
_model = None
_model_unavailable = False


def _get_model():
    """Load the sentence-transformers model (once, lazily).

    Uses all-MiniLM-L6-v2 by default (384 dims, ~80MB, fast on CPU).
    """
    global _model, _model_unavailable
    if _model is not None:
        return _model
    if _model_unavailable:
        return None

    try:
        from sentence_transformers import SentenceTransformer
        model_name = settings.EMBEDDING_MODEL
        logger.info("Loading embedding model from local cache: %s", model_name)
        _model = SentenceTransformer(model_name, local_files_only=True)
        logger.info("Embedding model loaded successfully")
        return _model
    except ImportError:
        logger.error(
            "sentence-transformers not installed. "
            "Install with: pip install sentence-transformers"
        )
        _model_unavailable = True
        return None
    except Exception as exc:
        _model_unavailable = True
        logger.warning(
            "Embedding model is not cached locally, disabling semantic search "
            "for this process: %s",
            exc,
        )
        return None


def warm_embedding_model() -> bool:
    """Best-effort warm-up so requests do not pay model load time."""
    return _get_model() is not None


# ═══════════════════════════════════════════════════════════════════
# Core embedding function
# ═══════════════════════════════════════════════════════════════════

def generate_embedding(
    text_input: str,
    *,
    allow_model_load: bool = True,
) -> list[float]:
    """Generate a 384-dim embedding for the given text.

    Uses sentence-transformers all-MiniLM-L6-v2 — completely free,
    no API calls, runs locally in ~10ms per text.
    """
    model = _get_model() if allow_model_load else _model
    if model is None:
        raise RuntimeError("Embedding model unavailable")
    embedding = model.encode(text_input, normalize_embeddings=True)
    return embedding.tolist()


# ═══════════════════════════════════════════════════════════════════
# Transaction embedding
# ═══════════════════════════════════════════════════════════════════

def _txn_to_embed_text(description: str, category: str, vendor: Optional[str] = None) -> str:
    """Build a rich text representation of a transaction for embedding."""
    parts = [description]
    if category and category != "Uncategorized":
        parts.append(f"category:{category}")
    if vendor:
        parts.append(f"vendor:{vendor}")
    return " | ".join(parts)


async def embed_transaction(txn_id, description: str, category: str,
                            vendor: Optional[str], db: AsyncSession,
                            workspace_id=None) -> None:
    """Generate and store an embedding for a single transaction.

    Called as a background task after transaction creation.

    M-005: workspace_id is required to enforce tenant isolation on the
    raw SQL UPDATE (ORM lifecycle is bypassed for pgvector columns).
    """
    try:
        embed_text = _txn_to_embed_text(description, category, vendor)
        embedding = generate_embedding(embed_text)

        # M-005: Raw SQL with workspace_id guard + updated_at touch
        vec_str = "[" + ",".join(str(f) for f in embedding) + "]"
        await db.execute(
            text(
                "UPDATE transactions "
                "SET description_vec = :vec, updated_at = NOW() "
                "WHERE id = :txn_id AND workspace_id = :ws_id"
            ),
            {
                "vec": vec_str,
                "txn_id": str(txn_id),
                "ws_id": str(workspace_id) if workspace_id else str(txn_id),
            },
        )
        await db.commit()

    except Exception as exc:
        logger.warning("Failed to embed transaction %s: %s", txn_id, exc)
        # Don't raise — embedding failure should never block transaction creation


@traced("embedding.batch")
async def batch_embed_transactions(workspace_id, db: AsyncSession) -> int:
    """Backfill embeddings for all transactions that don't have one yet.

    Returns the number of transactions embedded.
    """
    # Fetch un-embedded transactions
    result = await db.execute(
        text(
            "SELECT id, description, category, vendor FROM transactions "
            "WHERE workspace_id = :ws_id AND description_vec IS NULL "
            "ORDER BY created_at DESC LIMIT 500"
        ),
        {"ws_id": str(workspace_id)},
    )
    rows = result.fetchall()

    if not rows:
        return 0

    BATCH_SIZE = 50
    count = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        for row in batch:
            embed_text = _txn_to_embed_text(row.description, row.category, row.vendor)
            embedding = generate_embedding(embed_text)
            vec_str = "[" + ",".join(str(f) for f in embedding) + "]"
            await db.execute(
                text(
                    "UPDATE transactions "
                    "SET description_vec = :vec, updated_at = NOW() "
                    "WHERE id = :txn_id AND workspace_id = :ws_id"
                ),
                {
                    "vec": vec_str,
                    "txn_id": str(row.id),
                    "ws_id": str(workspace_id),
                },
            )
            count += 1
        # Yield control to the event loop between micro-batches
        # so other requests are not starved during bulk embedding
        await asyncio.sleep(0)

    await db.commit()
    logger.info("Batch-embedded %d transactions for workspace %s", count, workspace_id)
    return count


# ═══════════════════════════════════════════════════════════════════
# Semantic search via pgvector
# ═══════════════════════════════════════════════════════════════════

async def get_relevant_transactions(
    db: AsyncSession,
    workspace_id,
    query: str,
    top_k: int = 10,
):
    """Find semantically relevant transactions using vector similarity.

    Returns ORM-like rows with id, description, amount, category, date,
    and a similarity score.
    """
    try:
        query_embedding = generate_embedding(query, allow_model_load=False)
        vec_str = "[" + ",".join(str(f) for f in query_embedding) + "]"

        result = await db.execute(
            text(
                "SELECT id, description, amount, category, type, date, vendor, "
                "1 - (description_vec <=> CAST(:vec AS vector)) AS similarity "
                "FROM transactions "
                "WHERE workspace_id = :ws_id "
                "AND description_vec IS NOT NULL "
                "ORDER BY description_vec <=> CAST(:vec AS vector) "
                "LIMIT :top_k"
            ),
            {"vec": vec_str, "ws_id": str(workspace_id), "top_k": top_k},
        )
        return result.fetchall()

    except Exception as exc:
        logger.warning("Semantic search failed (pgvector may not be ready): %s", exc)
        return []
