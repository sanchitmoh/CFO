"""
AI CFO — Anomaly Detection Service (ML-003 / M-004)
Incremental anomaly detection with cached statistical models.

Instead of recomputing category stats from scratch on every scan,
we cache per-category statistics and only score new/unseen transactions.
Model stats are refreshed when transaction count grows by >20%.

M-004: Thresholds are calibrated **per-category** using Coefficient of
Variation (CV = stddev / mean), which is dimensionless and naturally
adapts to any currency, business size, or spending pattern.
"""
import math
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType, Workspace
from schemas import AnomalyOut, ScanResult
from cache import cache_get, cache_set, make_cache_key
from services.alert_engine import get_currency_symbol

logger = logging.getLogger(__name__)


async def _anchored_cutoff(db: AsyncSession, workspace_id, days: int) -> datetime:
    """Compute a date cutoff anchored to the latest transaction, not 'now'.

    This ensures historical CSVs (e.g. 2024 data imported in 2026) are
    visible to the anomaly scanner.
    """
    result = await db.execute(
        select(func.max(Transaction.date))
        .where(Transaction.workspace_id == workspace_id)
    )
    latest = result.scalar()
    if latest is None:
        return datetime.now(timezone.utc) - timedelta(days=days)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return latest - timedelta(days=days)

# ── M-004: Per-category threshold calibration ─────────────────────────
# CV (Coefficient of Variation) = stddev / mean.
# Dimensionless → works across currencies and business sizes.
#
# Low CV  (rent, salaries)  → tight threshold catches real outliers
# High CV (marketing, travel) → loose threshold avoids false positives

# Minimum transactions per category before we trust category-level stats.
# Below this, fall back to the workspace-wide default.
_MIN_CATEGORY_SAMPLE = 5

# Workspace-wide fallback when total expense count is sparse.
_SPARSE_DATA_THRESHOLD = 1.5
_SPARSE_DATA_CUTOFF = 30  # transactions

# When no anomalies exceed calibrated thresholds, surface top-N outliers
_TOP_OUTLIER_FALLBACK = 5
_TOP_OUTLIER_MIN_ZSCORE = 0.8  # minimum z-score to even be "noteworthy"


def _cv_to_threshold(cv: float) -> float:
    """Map a Coefficient of Variation to a z-score threshold.

    Uses a continuous linear interpolation clamped to [1.2, 3.0] so
    that there are no arbitrary cliff edges.

    CV range         Threshold   Typical categories
    ─────────────    ─────────   ──────────────────
    ≤ 0.10           1.2        Rent, loan payments
    0.10 – 0.30      ~1.3–1.6   Utilities, SaaS subscriptions
    0.30 – 0.80      ~1.6–2.2   Marketing, travel
    ≥ 1.50           3.0        Highly volatile / one-off spend
    """
    # Linear interpolation: threshold = 1.2 + cv * 1.2, clamped [1.2, 3.0]
    return max(1.2, min(3.0, 1.2 + cv * 1.2))


async def calibrate_category_thresholds(
    workspace_id,
    db: AsyncSession,
    *,
    explicit_override: float | None = None,
) -> dict[str, float]:
    """M-004: Compute per-category z-score thresholds via CV analysis.

    Returns:
        Dict mapping category name → z-threshold.
        A special key ``"__default__"`` provides the workspace fallback
        for categories with insufficient data.

    If ``explicit_override`` is provided (user passed ``z_threshold`` in
    the API), every category gets that value — full user control.
    """
    # ── Fast path: user-supplied override ─────────────────────────
    if explicit_override is not None:
        return {"__default__": explicit_override}

    # ── Per-category aggregation ──────────────────────────────────
    result = await db.execute(
        select(
            Transaction.category,
            func.avg(Transaction.amount),
            func.stddev(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(and_(
            Transaction.workspace_id == workspace_id,
            Transaction.type == TransactionType.expense,
        ))
        .group_by(Transaction.category)
    )
    rows = result.all()

    total_count = sum(int(r[3] or 0) for r in rows)
    thresholds: dict[str, float] = {}

    # Workspace-level fallback: aggregate CV across all expenses
    all_means = []
    all_stddevs = []

    for category, avg_val, std_val, count in rows:
        mean = float(avg_val) if avg_val is not None else 0.0
        std = float(std_val) if std_val is not None else 0.0
        n = int(count or 0)

        all_means.append(mean * n)   # weighted contribution
        all_stddevs.append(std)

        # Only trust per-category calibration with enough samples
        if n >= _MIN_CATEGORY_SAMPLE and mean > 0:
            cv = std / mean
            thresholds[category] = _cv_to_threshold(cv)

    # ── Compute workspace-level default ───────────────────────────
    if total_count < _SPARSE_DATA_CUTOFF:
        workspace_default = _SPARSE_DATA_THRESHOLD
    elif total_count > 0 and all_means:
        # Weighted mean across categories
        total_spend = sum(all_means)
        weighted_mean = total_spend / total_count if total_count else 1.0
        # Use median stddev as a robust estimator
        sorted_stds = sorted(all_stddevs)
        median_std = sorted_stds[len(sorted_stds) // 2] if sorted_stds else 0.0
        workspace_cv = median_std / weighted_mean if weighted_mean > 0 else 0.5
        workspace_default = _cv_to_threshold(workspace_cv)
    else:
        workspace_default = _SPARSE_DATA_THRESHOLD

    thresholds["__default__"] = workspace_default

    logger.info(
        "Calibrated thresholds for workspace %s: %d categories, default=%.2f",
        workspace_id, len(thresholds) - 1, workspace_default,
    )
    return thresholds


# ── Backwards-compatible wrapper ──────────────────────────────────────
async def calibrate_threshold(workspace_id, db: AsyncSession) -> float:
    """Legacy single-value calibration — returns the workspace default.

    Kept for any callers that expect a single float (e.g. alert_engine).
    """
    thresholds = await calibrate_category_thresholds(workspace_id, db)
    return thresholds["__default__"]


async def _get_category_stats(
    db: AsyncSession, ws_id, cutoff: datetime
) -> dict[str, dict]:
    """
    Compute per-category mean/std/count for expenses.
    Returns: {category: {mean, std, count, cv, threshold, amounts}}
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
        cv = std / mean if mean > 0 else 0.0
        stats["mean"] = mean
        stats["std"] = std
        stats["cv"] = round(cv, 4)

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
    z_threshold: float | None = None,
    days: int = 90,
) -> ScanResult:
    """
    Scan for anomalies using cached z-score model with per-category thresholds.

    Args:
        z_threshold: Explicit override (applies uniformly to all categories).
                     If None, per-category CV-based calibration is used (M-004).

    Flow:
    1. Calibrate per-category thresholds (or use explicit override)
    2. Check if model needs rebuilding (>20% transaction growth)
    3. If cached model is fresh, load stats from Redis
    4. Otherwise, rebuild from DB and cache
    5. Score only un-scanned transactions when possible
    """
    ws = await db.get(Workspace, workspace_id)
    sym = get_currency_symbol(ws.currency if ws else "USD")

    # M-004: Per-category threshold calibration
    cat_thresholds = await calibrate_category_thresholds(
        workspace_id, db, explicit_override=z_threshold
    )
    default_threshold = cat_thresholds["__default__"]

    cutoff = await _anchored_cutoff(db, workspace_id, days)
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
            cat: {
                "mean": s["mean"],
                "std": s["std"],
                "count": s["count"],
                "cv": s.get("cv", 0.0),
            }
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

        # M-004: Use per-category threshold, fall back to workspace default
        effective_threshold = cat_thresholds.get(cat, default_threshold)

        if z_score >= effective_threshold:
            direction = "above" if float(txn.amount) > mean else "below"
            reason = (
                f"Amount {sym}{float(txn.amount):,.2f} is {z_score:.1f} standard deviations "
                f"{direction} the {cat} average of {sym}{mean:,.2f} "
                f"(threshold: {effective_threshold:.1f}σ)"
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

    # ── Top-outlier fallback ──────────────────────────────────────
    # If no anomalies exceeded calibrated thresholds, surface the
    # top N highest z-score transactions as "noteworthy" so the CFO
    # dashboard always has actionable insights.
    if not anomalies and len(transactions) >= 10:
        scored = [
            (txn, float(txn.anomaly_score or 0))
            for txn in transactions
            if (txn.anomaly_score or 0) >= _TOP_OUTLIER_MIN_ZSCORE
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        for txn, z_score in scored[:_TOP_OUTLIER_FALLBACK]:
            cat = txn.category
            stats = (cached_stats or category_stats).get(cat, {})
            mean = stats.get("mean", 0)
            effective_threshold = cat_thresholds.get(cat, default_threshold)
            direction = "above" if float(txn.amount) > mean else "below"
            reason = (
                f"Noteworthy: Amount {sym}{float(txn.amount):,.2f} is {z_score:.1f}σ "
                f"{direction} the {cat} average of {sym}{mean:,.2f} "
                f"(below threshold {effective_threshold:.1f}σ, surfaced as top outlier)"
            )
            txn.is_anomaly = True
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
        if anomalies:
            await db.commit()
            logger.info(
                "No calibrated anomalies — surfaced %d top outliers for workspace %s",
                len(anomalies), workspace_id,
            )

    return ScanResult(
        scanned=len(transactions),
        anomalies_found=len(anomalies),
        anomalies=anomalies,
    )


async def scan_anomalies_stream(
    db: AsyncSession,
    workspace_id,
    z_threshold: float | None = None,
    days: int = 90,
):
    """L-001: Streaming variant of scan_anomalies.

    Yields ``(event_type, payload)`` tuples as each transaction is scored:
      - ``("progress", {"scanned": n})`` — periodic progress updates
      - ``("anomaly", {AnomalyOut fields})`` — each detected anomaly
      - ``("done", {"scanned": n, "anomalies_found": m})`` — final summary

    This allows the router to emit SSE events without waiting for the
    full scan to complete.
    """
    ws = await db.get(Workspace, workspace_id)
    sym = get_currency_symbol(ws.currency if ws else "USD")

    cat_thresholds = await calibrate_category_thresholds(
        workspace_id, db, explicit_override=z_threshold
    )
    default_threshold = cat_thresholds["__default__"]

    cutoff = await _anchored_cutoff(db, workspace_id, days)
    cache_key = make_cache_key("anomaly_stats", str(workspace_id))

    # Reuse the same model-caching logic as scan_anomalies
    needs_rebuild, current_count = await _should_rebuild_model(
        db, workspace_id, cutoff
    )

    cached_stats = None
    if not needs_rebuild:
        cached_stats = await cache_get(cache_key)

    if cached_stats:
        category_stats = cached_stats
    else:
        category_stats = await _get_category_stats(db, workspace_id, cutoff)
        serializable = {
            cat: {
                "mean": s["mean"],
                "std": s["std"],
                "count": s["count"],
                "cv": s.get("cv", 0.0),
            }
            for cat, s in category_stats.items()
        }
        await cache_set(cache_key, serializable, ttl=3600)
        await cache_set(
            make_cache_key("anomaly_model_count", str(workspace_id)),
            {"count": current_count},
            ttl=3600,
        )

    # Fetch transactions
    if cached_stats and not needs_rebuild:
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
    total = len(transactions)

    if total < 3:
        yield ("done", {"scanned": total, "anomalies_found": 0})
        return

    anomalies_found = 0
    for i, txn in enumerate(transactions):
        cat = txn.category
        if cached_stats:
            stats = cached_stats.get(cat, {})
        else:
            stats = category_stats.get(cat, {})

        mean = stats.get("mean", 0)
        std = stats.get("std", 0)

        if std == 0:
            txn.is_anomaly = False
            txn.anomaly_score = 0
        else:
            z_score = abs(float(txn.amount) - mean) / std
            effective_threshold = cat_thresholds.get(cat, default_threshold)

            if z_score >= effective_threshold:
                direction = "above" if float(txn.amount) > mean else "below"
                reason = (
                    f"Amount {sym}{float(txn.amount):,.2f} is {z_score:.1f} standard deviations "
                    f"{direction} the {cat} average of {sym}{mean:,.2f} "
                    f"(threshold: {effective_threshold:.1f}\u03c3)"
                )
                txn.is_anomaly = True
                txn.anomaly_score = round(z_score, 3)
                anomalies_found += 1

                yield ("anomaly", {
                    "id": str(txn.id),
                    "date": txn.date.isoformat() if hasattr(txn.date, "isoformat") else str(txn.date),
                    "description": txn.description,
                    "amount": float(txn.amount),
                    "category": txn.category,
                    "type": txn.type.value,
                    "account": txn.account,
                    "anomaly_score": round(z_score, 3),
                    "reason": reason,
                })
            else:
                txn.is_anomaly = False
                txn.anomaly_score = round(z_score, 3)

        # Emit progress every 50 transactions
        if (i + 1) % 50 == 0:
            yield ("progress", {"scanned": i + 1, "total": total})

    await db.commit()

    yield ("done", {"scanned": total, "anomalies_found": anomalies_found})

