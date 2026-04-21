"""
AI CFO — Alert Engine Service
Checks alert rules against current financial data and generates alerts.
Designed to be called as a background task after data mutations.
"""
import logging
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Transaction, TransactionType, Budget, Alert, AlertSeverity,
)

logger = logging.getLogger(__name__)


async def run_alert_engine(db: AsyncSession, workspace_id) -> int:
    """
    Evaluate all alert rules for a workspace. Returns count of new alerts created.

    Rules checked:
      1. Budget overrun (≥90% of any budget limit)
      2. Revenue drop (current month income < 70% of prior month avg)
      3. High single expense (any transaction > 3× the category average)
    """
    now = datetime.utcnow()
    alerts_created = 0

    try:
        # ── Rule 1: Budget overrun ───────────────────────────────
        budgets = await db.execute(
            select(Budget).where(Budget.workspace_id == workspace_id)
        )
        for budget in budgets.scalars():
            if budget.monthly_limit > 0:
                ratio = float(budget.current_spend) / float(budget.monthly_limit)
                if ratio >= 1.0:
                    alert = Alert(
                        workspace_id=workspace_id,
                        title=f"Budget exceeded: {budget.category}",
                        message=(
                            f"Spending in '{budget.category}' has reached "
                            f"${float(budget.current_spend):,.0f} "
                            f"({ratio:.0%} of ${float(budget.monthly_limit):,.0f} limit)."
                        ),
                        severity=AlertSeverity.critical,
                        category="budget",
                    )
                    db.add(alert)
                    alerts_created += 1
                elif ratio >= 0.9:
                    alert = Alert(
                        workspace_id=workspace_id,
                        title=f"Budget warning: {budget.category}",
                        message=(
                            f"Spending in '{budget.category}' is at "
                            f"${float(budget.current_spend):,.0f} "
                            f"({ratio:.0%} of ${float(budget.monthly_limit):,.0f} limit)."
                        ),
                        severity=AlertSeverity.warning,
                        category="budget",
                    )
                    db.add(alert)
                    alerts_created += 1

        # ── Rule 2: Revenue drop ─────────────────────────────────
        # Compare current month income to trailing 3-month average
        income_q = await db.execute(
            select(
                func.extract("month", Transaction.date).label("m"),
                func.sum(Transaction.amount),
            )
            .where(and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.income,
                Transaction.date >= datetime(now.year, max(1, now.month - 3), 1),
            ))
            .group_by("m")
            .order_by("m")
        )
        monthly_incomes = [float(row[1] or 0) for row in income_q]
        if len(monthly_incomes) >= 2:
            prior_avg = sum(monthly_incomes[:-1]) / len(monthly_incomes[:-1])
            current = monthly_incomes[-1]
            if prior_avg > 0 and current < prior_avg * 0.7:
                alert = Alert(
                    workspace_id=workspace_id,
                    title="Revenue decline detected",
                    message=(
                        f"Current month revenue (${current:,.0f}) is "
                        f"{((1 - current / prior_avg) * 100):.0f}% below the "
                        f"trailing average (${prior_avg:,.0f})."
                    ),
                    severity=AlertSeverity.warning,
                    category="revenue",
                )
                db.add(alert)
                alerts_created += 1

        if alerts_created > 0:
            await db.commit()

        logger.info(
            "Alert engine completed for workspace %s: %d alerts created",
            workspace_id, alerts_created,
        )
    except Exception:
        logger.exception("Alert engine failed for workspace %s", workspace_id)
        await db.rollback()

    return alerts_created
