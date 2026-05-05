"""
AI CFO — Industry Benchmarks Router (Feature C)
Compare workspace metrics against industry averages.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Transaction, TransactionType, IndustryBenchmark, Workspace
from schemas import BenchmarkInsight
from cache import cache_get, cache_set, make_versioned_cache_key

router = APIRouter()


@router.get("/", response_model=list[BenchmarkInsight])
async def get_benchmarks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """
    Compare the workspace's financial metrics against industry benchmarks.
    Returns insights for each available metric.
    """
    ws_id = user.workspace_id
    cache_key = await make_versioned_cache_key("benchmarks", str(ws_id))

    # LOW-003: Cache check and compute are atomic per request, but concurrent
    # requests may still both miss and compute. This is acceptable as it only
    # wastes compute, not correctness. A distributed lock would add complexity
    # for minimal benefit.
    cached = await cache_get(cache_key)
    if cached:
        return [BenchmarkInsight(**item) for item in cached]

    # Get workspace industry
    ws_q = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    workspace = ws_q.scalar_one_or_none()
    industry = workspace.industry if workspace else "general_smb"

    # CRIT-006: Use MAX(Transaction.date) as the temporal anchor instead of
    # datetime.now(). For historical-data workspaces (e.g. 2022-2024 CSV
    # imported in 2026), now()-365d returns zero results.
    date_anchor_q = await db.execute(
        select(func.max(Transaction.date)).where(
            Transaction.workspace_id == ws_id
        )
    )
    latest_date = date_anchor_q.scalar()
    if latest_date is None:
        latest_date = datetime.now(timezone.utc)
    elif latest_date.tzinfo is None:
        latest_date = latest_date.replace(tzinfo=timezone.utc)
    cutoff = latest_date - timedelta(days=365)

    totals = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.date >= cutoff,
            )
        )
        .group_by(Transaction.type)
    )

    income = 0.0
    expenses = 0.0
    for row in totals:
        if row[0] == TransactionType.income:
            income = float(row[1] or 0)
        else:
            expenses = float(row[1] or 0)

    # LOW-005: Compute workspace metrics
    profit_margin = ((income - expenses) / income * 100) if income > 0 else 0
    expense_ratio = (expenses / income * 100) if income > 0 else 0

    your_metrics = {
        "profit_margin": round(profit_margin, 1),
        "expense_ratio": round(expense_ratio, 1),
        "revenue_growth": 0.0,  # Would need historical comparison
    }

    # ── Get industry benchmarks from DB ───────────────────────────
    bench_q = await db.execute(
        select(IndustryBenchmark)
        .where(IndustryBenchmark.industry == industry)
        .order_by(IndustryBenchmark.metric_name)
    )
    benchmarks = list(bench_q.scalars())

    # If no benchmarks in DB, use defaults
    if not benchmarks:
        default_benchmarks = [
            {"metric_name": "profit_margin", "metric_value": 15.0, "unit": "percentage"},
            {"metric_name": "expense_ratio", "metric_value": 75.0, "unit": "percentage"},
            {"metric_name": "revenue_growth", "metric_value": 10.0, "unit": "percentage"},
        ]
        benchmarks_data = default_benchmarks
    else:
        benchmarks_data = [
            {
                "metric_name": b.metric_name,
                "metric_value": float(b.metric_value),
                "unit": b.unit,
            }
            for b in benchmarks
        ]

    # ── Build comparison insights ─────────────────────────────────
    insights = []
    for bench in benchmarks_data:
        name = bench["metric_name"]
        bench_val = bench["metric_value"]
        your_val = your_metrics.get(name, 0.0)

        if bench_val != 0:
            delta_pct = round((your_val - bench_val) / bench_val * 100, 1)
        else:
            delta_pct = 0.0

        # Determine status
        if name in ("profit_margin", "revenue_growth"):
            # Higher is better
            if delta_pct > 5:
                status_ = "above"
                insight = f"Your {name.replace('_', ' ')} of {your_val}% exceeds the industry average by {abs(delta_pct)}%."
            elif delta_pct < -5:
                status_ = "below"
                insight = f"Your {name.replace('_', ' ')} of {your_val}% is below industry average by {abs(delta_pct)}%. Consider strategies to improve."
            else:
                status_ = "on_par"
                insight = f"Your {name.replace('_', ' ')} of {your_val}% is in line with industry standards."
        else:
            # Lower is better (expense_ratio)
            if delta_pct < -5:
                status_ = "above"
                insight = f"Your {name.replace('_', ' ')} of {your_val}% is better than the {bench_val}% industry average."
            elif delta_pct > 5:
                status_ = "below"
                insight = f"Your {name.replace('_', ' ')} of {your_val}% is higher than the {bench_val}% industry average. Look for cost savings."
            else:
                status_ = "on_par"
                insight = f"Your {name.replace('_', ' ')} is within normal range for {industry.replace('_', ' ')}."

        insights.append(BenchmarkInsight(
            metric_name=name,
            your_value=your_val,
            benchmark_value=bench_val,
            unit=bench["unit"],
            delta_pct=delta_pct,
            insight=insight,
            status=status_,
        ))

    # Cache for 1 hour
    await cache_set(cache_key, [i.model_dump() for i in insights], ttl=3600)
    return insights
