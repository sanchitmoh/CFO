"""
AI CFO — Anomaly Detection Router
Thin HTTP adapter over anomaly_service (ML-003).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_db_context
from auth import get_current_user
from models import User, Transaction
from schemas import AnomalyOut, ScanResult
from services.audit_service import log_action
from services.anomaly_service import scan_anomalies
from services.alert_engine import run_alert_engine

router = APIRouter()


@router.get("/scan", response_model=ScanResult)
async def scan_anomalies_endpoint(
    z_threshold: float = Query(2.0, ge=1.0, le=4.0),
    days: int = Query(90, ge=30, le=365),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan recent transactions for statistical anomalies."""
    result = await scan_anomalies(db, user.workspace_id, z_threshold, days)

    if result.anomalies_found > 0:
        await log_action(
            db, user, "anomaly.scan", "transaction",
            new_value={"scanned": result.scanned, "found": result.anomalies_found},
        )

        # ARCH-004: Trigger alert engine in background
        async def _run_alerts():
            async with get_db_context() as bg_db:
                await run_alert_engine(bg_db, user.workspace_id)

        background_tasks.add_task(_run_alerts)

    return result


@router.get("/", response_model=list[AnomalyOut])
async def list_flagged_anomalies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all previously flagged anomalies."""
    result = await db.execute(
        select(Transaction)
        .where(and_(
            Transaction.workspace_id == user.workspace_id,
            Transaction.is_anomaly.is_(True),
        ))
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
