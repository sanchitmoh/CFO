"""
AI CFO — Reports Router
Generate financial reports with date range filtering.
"""
from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType
from schemas import ReportSummary, CategorySummary

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a financial summary report for the given period."""
    ws_id = user.workspace_id
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    # ── Totals ────────────────────────────────────────────────────
    totals = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .group_by(Transaction.type)
    )

    income = 0.0
    expenses = 0.0
    txn_count = 0
    for row in totals:
        if row[0] == TransactionType.income:
            income = float(row[1] or 0)
        else:
            expenses = float(row[1] or 0)
        txn_count += int(row[2] or 0)

    # ── Expense by category ──────────────────────────────────────
    cats_q = await db.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )

    expense_by_cat = [
        CategorySummary(category=r[0], total=float(r[1]), count=int(r[2]))
        for r in cats_q
    ]

    # ── Top vendors ──────────────────────────────────────────────
    vendor_q = await db.execute(
        select(
            Transaction.vendor,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.vendor.isnot(None),
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .group_by(Transaction.vendor)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(10)
    )

    top_vendors = [
        {"vendor": r[0], "total": float(r[1]), "count": int(r[2])}
        for r in vendor_q
    ]

    return ReportSummary(
        period_start=start,
        period_end=end,
        total_income=income,
        total_expenses=expenses,
        net_cash_flow=income - expenses,
        transaction_count=txn_count,
        expense_by_category=expense_by_cat,
        top_vendors=top_vendors,
    )
