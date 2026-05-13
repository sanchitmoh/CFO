"""AI CFO — Anomaly Detection Router

Thin HTTP adapter over anomaly_service (ML-003).
L-001: SSE streaming endpoint for large scan results.
L-002: Redis-backed scan cooldown for multi-worker deployments.
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from dependencies import get_rls_db
from auth import get_current_user
from cache import get_redis
from models import User, Transaction
from schemas import AnomalyOut, ScanResult
from services.audit_service import log_action
from services.anomaly_service import scan_anomalies, scan_anomalies_stream
from services.alert_engine import run_alert_engine

logger = logging.getLogger(__name__)
router = APIRouter()

# ── L-002: Redis-backed cooldown (replaces in-memory dict) ───────
_SCAN_COOLDOWN_SECONDS = 60


async def _check_scan_cooldown(workspace_id: str) -> None:
    """L-002: Enforce per-workspace scan cooldown via Redis SETEX.

    Uses a Redis key with TTL so the cooldown is shared across all
    Uvicorn workers.  Degrades gracefully — if Redis is unreachable
    the scan is allowed (fail-open).
    
    INFRA-002: Circuit breaker pattern — catches Redis errors and allows
    operation to continue rather than hard-failing.
    """
    try:
        r = await get_redis()
        cd_key = f"cooldown:anomaly_scan:{workspace_id}"
        if await r.exists(cd_key):
            ttl = await r.ttl(cd_key)
            remaining = max(ttl, 1)
            raise HTTPException(
                status_code=429,
                detail=f"Scan rate limited. Try again in {remaining} seconds.",
                headers={"Retry-After": str(remaining)},
            )
        await r.setex(cd_key, _SCAN_COOLDOWN_SECONDS, "1")
    except HTTPException:
        raise  # re-raise 429
    except Exception as exc:
        # INFRA-002: Redis down → fail-open, allow the scan
        logger.warning("Redis cooldown check failed — allowing scan: %s", exc)


@router.get("/scan", response_model=ScanResult)
async def scan_anomalies_endpoint(
    z_threshold: Optional[float] = Query(None, ge=1.0, le=4.0),
    days: int = Query(90, ge=30, le=365),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Scan recent transactions for statistical anomalies.

    If ``z_threshold`` is omitted, the service auto-calibrates based
    on the workspace's historical spend variance (EXT-003).

    L-002: Rate-limited to one scan per workspace per 60 seconds via Redis.
    """
    await _check_scan_cooldown(str(user.workspace_id))

    result = await scan_anomalies(db, user.workspace_id, z_threshold, days)

    if result.anomalies_found > 0:
        await log_action(
            db, user, "anomaly.scan", "transaction",
            new_value={"scanned": result.scanned, "found": result.anomalies_found},
        )

        # ARCH-004: Trigger alert engine in background
        async def _run_alerts():
            # HIGH-003: Use RLS-bound session for tenant-isolated alerts
            from database import get_rls_db_context
            async with get_rls_db_context(str(user.workspace_id)) as bg_db:
                await run_alert_engine(bg_db, user.workspace_id)

        background_tasks.add_task(_run_alerts)

    return result


@router.get("/scan/stream")
async def scan_anomalies_sse(
    z_threshold: Optional[float] = Query(None, ge=1.0, le=4.0),
    days: int = Query(90, ge=30, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """L-001: Stream anomaly scan results as Server-Sent Events.

    Each anomaly is emitted as an ``event: anomaly`` SSE message.
    A final ``event: done`` message carries the scan summary.

    This avoids blocking the response until the entire scan completes,
    which matters for workspaces with 1000+ transactions.
    """
    await _check_scan_cooldown(str(user.workspace_id))

    # MED-004: Max SSE stream duration to prevent indefinite DB session hold
    _SSE_TIMEOUT_SECONDS = 120

    async def _event_generator():
        import time
        deadline = time.monotonic() + _SSE_TIMEOUT_SECONDS
        scanned = 0
        found = 0
        try:
            async for event_type, payload in scan_anomalies_stream(
                db, user.workspace_id, z_threshold, days
            ):
                # MED-004: Enforce hard deadline per iteration
                if time.monotonic() > deadline:
                    logger.warning(
                        "SSE stream timed out after %ds (scanned=%d, found=%d)",
                        _SSE_TIMEOUT_SECONDS, scanned, found,
                    )
                    yield f'event: error\ndata: {{"error": "Stream timeout after {_SSE_TIMEOUT_SECONDS}s"}}\n\n'
                    return

                if event_type == "anomaly":
                    found += 1
                    data = json.dumps(payload, default=str)
                    yield f"event: anomaly\ndata: {data}\n\n"
                elif event_type == "progress":
                    scanned = payload.get("scanned", scanned)
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                elif event_type == "done":
                    scanned = payload.get("scanned", scanned)
                    found = payload.get("anomalies_found", found)
                    yield f"event: done\ndata: {json.dumps(payload)}\n\n"

            # Log if anomalies found
            if found > 0:
                await log_action(
                    db, user, "anomaly.scan.stream", "transaction",
                    new_value={"scanned": scanned, "found": found},
                )
        except asyncio.CancelledError:
            # Client disconnected — release resources cleanly
            logger.info("SSE client disconnected (scanned=%d, found=%d)", scanned, found)
            return
        except GeneratorExit:
            logger.info("SSE generator closed (scanned=%d, found=%d)", scanned, found)
            return

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/", response_model=list[AnomalyOut])
async def list_flagged_anomalies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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
            account=txn.account or "Unknown",  # LOW-002: Handle None account
            anomaly_score=txn.anomaly_score or 0,
            reason=f"Previously flagged anomaly (score: {(txn.anomaly_score or 0):.1f})",
        )
        for txn in result.scalars()
    ]
