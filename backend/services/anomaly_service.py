"""
AI CFO — Anomaly Detection Service (ML-003)
Incremental anomaly detection with cached statistical models.

Instead of recomputing category stats from scratch on every scan,
we cache per-category statistics and only score new/unseen transactions.
Model stats are refreshed when transaction count grows by >20%.
"""
import math
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType
from schemas import AnomalyOut, ScanResult
from cache import cache_get, cache_set, make_cache_key

logger = logging.getLogger(__name__)


async def _get_category_stats(
    db: AsyncSession, ws_id, cutoff: datetime
) -> dict[str, dict]:
    """
    Compute per-category mean/std/count for expenses.
    Returns: {category: {mean, std, count, amounts}}
    """
    result = await db.execute(
        select(Transaction)
        .where(and_(
            Transaction.workspace_id == ws_id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= cutoff,
        ))
        .order_by(Transaction.date.desc())
    )
    transactions = list(result.scalars())

    category_stats: dict[str, dict] = {}
    for txn in transactions:
        cat = txn.category
        if cat not in category_stats:
            category_stats[cat] = {"amounts": [], "count": 0, "ids": []}
        category_stats[cat]["amounts"].append(float(txn.amount))
        category_stats[cat]["count"] += 1
        category_stats[cat]["ids"].append(str(txn.id))

    for cat, stats in category_stats.items():
        amounts = stats["amounts"]
        n = len(amounts)
        mean = sum(amounts) / n
        variance = sum((x - mean) ** 2 for x in amounts) / max(n - 1, 1)
        std = math.sqrt(variance)
        stats["mean"] = mean
        stats["std"] = std

    return category_stats


async def _should_rebuild_model(
    db: AsyncSession, ws_id, cutoff: datetime
) -> tuple[bool, int]:
    """
    Check if we need to rebuild category stats.
    Returns (should_rebuild, current_count).
    """
    cache_key = make_cache_key("anomaly_model_count", str(ws_id))
    cached_count = await cache_get(cache_key)

    current_count_q = await db.execute(
        select(func.count(Transaction.id))
        .where(and_(
            Transaction.workspace_id == ws_id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= cutoff,
        ))
    )
    current_count = current_count_q.scalar() or 0

    if cached_count is None:
        return True, current_count

    old_count = int(cached_count.get("count", 0))
    if old_count == 0:
        return True, current_count

    growth = (current_count - old_count) / old_count
    # Rebuild if >20% growth
    return growth > 0.20, current_count


async def scan_anomalies(
    db: AsyncSession,
    workspace_id,
    z_threshold: float = 2.0,
    days: int = 90,
) -> ScanResult:
    """
    Scan for anomalies using cached z-score model.

    Flow:
    1. Check if model needs rebuilding (>20% transaction growth)
    2. If cached model is fresh, load stats from Redis
    3. Otherwise, rebuild from DB and cache
    4. Score only un-scanned transactions when possible
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    cache_key = make_cache_key("anomaly_stats", str(workspace_id))

    # Check if model rebuild is needed
    needs_rebuild, current_count = await _should_rebuild_model(
        db, workspace_id, cutoff
    )

    # Try cached stats
    cached_stats = None
    if not needs_rebuild:
        cached_stats = await cache_get(cache_key)

    if cached_stats:
        category_stats = cached_stats
        logger.info("Using cached anomaly model for workspace %s", workspace_id)
    else:
        # Rebuild model
        category_stats = await _get_category_stats(db, workspace_id, cutoff)

        # Cache the serializable stats (without SQLAlchemy objects)
        serializable = {
            cat: {"mean": s["mean"], "std": s["std"], "count": s["count"]}
            for cat, s in category_stats.items()
        }
        await cache_set(cache_key, serializable, ttl=3600)  # 1 hour
        await cache_set(
            make_cache_key("anomaly_model_count", str(workspace_id)),
            {"count": current_count},
            ttl=3600,
        )
        logger.info("Rebuilt anomaly model for workspace %s (%d txns)", workspace_id, current_count)

    # ── Score transactions ────────────────────────────────────────
    # Fetch un-scanned transactions first, fall back to all if model was rebuilt
    if cached_stats and not needs_rebuild:
        # Incremental: only score transactions not yet scanned
        txn_q = await db.execute(
            select(Transaction)
            .where(and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= cutoff,
                Transaction.is_anomaly == None,  # noqa: E711
            ))
            .order_by(Transaction.date.desc())
        )
    else:
        # Full scan
        txn_q = await db.execute(
            select(Transaction)
            .where(and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= cutoff,
            ))
            .order_by(Transaction.date.desc())
        )

    transactions = list(txn_q.scalars())

    if len(transactions) < 3:
        return ScanResult(scanned=len(transactions), anomalies_found=0, anomalies=[])

    anomalies: list[AnomalyOut] = []
    for txn in transactions:
        cat = txn.category
        # Use cached stats if available, otherwise use rebuilt stats
        if cached_stats:
            stats = cached_stats.get(cat, {})
        else:
            stats = category_stats.get(cat, {})

        mean = stats.get("mean", 0)
        std = stats.get("std", 0)

        if std == 0:
            txn.is_anomaly = False
            txn.anomaly_score = 0
            continue

        z_score = abs(float(txn.amount) - mean) / std

        if z_score >= z_threshold:
            direction = "above" if float(txn.amount) > mean else "below"
            reason = (
                f"Amount ${float(txn.amount):,.2f} is {z_score:.1f} standard deviations "
                f"{direction} the {cat} average of ${mean:,.2f}"
            )
            txn.is_anomaly = True
            txn.anomaly_score = round(z_score, 3)

            anomalies.append(AnomalyOut(
                id=txn.id,
                date=txn.date,
                description=txn.description,
                amount=float(txn.amount),
                category=txn.category,
                type=txn.type.value,
                account=txn.account,
                anomaly_score=round(z_score, 3),
                reason=reason,
            ))
        else:
            txn.is_anomaly = False
            txn.anomaly_score = round(z_score, 3)

    await db.commit()

    return ScanResult(
        scanned=len(transactions),
        anomalies_found=len(anomalies),
        anomalies=anomalies,
    )
