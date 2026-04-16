"""
AI CFO — Anomaly Detection Router
Z-score based anomaly detection with per-category analysis.
"""
import uuid
from datetime import datetime, timedelta
import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType
from schemas import AnomalyOut, ScanResult
from services.audit_service import log_action

router = APIRouter()


@router.get("/scan", response_model=ScanResult)
async def scan_anomalies(
    z_threshold: float = Query(2.0, ge=1.0, le=4.0),
    days: int = Query(90, ge=30, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan recent transactions for statistical anomalies using z-scores."""
    ws_id = user.workspace_id
    cutoff = datetime.utcnow() - timedelta(days=days)

    # ── Get all expense transactions ──────────────────────────────
    result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= cutoff,
            )
        )
        .order_by(Transaction.date.desc())
    )
    transactions = list(result.scalars())

    if len(transactions) < 3:
        return ScanResult(scanned=len(transactions), anomalies_found=0, anomalies=[])

    # ── Compute per-category stats ────────────────────────────────
    category_stats: dict[str, dict] = {}
    for txn in transactions:
        cat = txn.category
        if cat not in category_stats:
            category_stats[cat] = {"amounts": [], "count": 0}
        category_stats[cat]["amounts"].append(float(txn.amount))
        category_stats[cat]["count"] += 1

    for cat, stats in category_stats.items():
        amounts = stats["amounts"]
        n = len(amounts)
        mean = sum(amounts) / n
        variance = sum((x - mean) ** 2 for x in amounts) / max(n - 1, 1)
        std = math.sqrt(variance)
        stats["mean"] = mean
        stats["std"] = std

    # ── Flag anomalies ────────────────────────────────────────────
    anomalies = []
    for txn in transactions:
        stats = category_stats.get(txn.category, {})
        mean = stats.get("mean", 0)
        std = stats.get("std", 0)

        if std == 0:
            continue

        z_score = abs(float(txn.amount) - mean) / std

        if z_score >= z_threshold:
            direction = "above" if float(txn.amount) > mean else "below"
            reason = (
                f"Amount ${float(txn.amount):,.2f} is {z_score:.1f} standard deviations "
                f"{direction} the {txn.category} average of ${mean:,.2f}"
            )

            # Mark in DB
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

    await db.commit()

    if anomalies:
        await log_action(
            db, user, "anomaly.scan", "transaction",
            new_value={"scanned": len(transactions), "found": len(anomalies)},
        )

    return ScanResult(
        scanned=len(transactions),
        anomalies_found=len(anomalies),
        anomalies=anomalies,
    )


@router.get("/", response_model=list[AnomalyOut])
async def list_flagged_anomalies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all previously flagged anomalies."""
    result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.workspace_id == user.workspace_id,
                Transaction.is_anomaly == True,
            )
        )
        .order_by(Transaction.date.desc())
        .limit(50)
    )

    return [
        AnomalyOut(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            amount=float(txn.amount),
            category=txn.category,
            type=txn.type.value,
            account=txn.account,
            anomaly_score=txn.anomaly_score or 0,
            reason=f"Previously flagged anomaly (score: {txn.anomaly_score:.1f})",
        )
        for txn in result.scalars()
    ]
