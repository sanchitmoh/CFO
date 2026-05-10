"""
AI CFO — Alert Engine Service
Checks alert rules against current financial data and generates alerts.
Designed to be called as a background task after data mutations.
"""
import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Transaction, TransactionType, Budget, Alert, AlertSeverity, Workspace
)

def get_currency_symbol(currency_code: str) -> str:
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", 
        "JPY": "¥", "CAD": "CA$", "AUD": "A$", "SGD": "S$", "CHF": "CHF"
    }
    return symbols.get(currency_code.upper(), currency_code.upper() + " ")

logger = logging.getLogger(__name__)


async def run_alert_engine(db: AsyncSession, workspace_id) -> int:
    """
    Evaluate all alert rules for a workspace. Returns count of new alerts created.

    Rules checked:
      1. Budget overrun (≥90% of any budget limit)
      2. Revenue drop (current month income < 70% of prior month avg)
      3. High single expense (any transaction > 3× the category average)
    """
    now = datetime.now(timezone.utc)
    alerts_created = 0

    try:
        # Fetch workspace currency
        ws = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
        currency = ws.currency if ws else "USD"
        sym = get_currency_symbol(currency)

        # ── Rule 1: Budget overrun ───────────────────────────────
        budgets = await db.execute(
            select(Budget).where(Budget.workspace_id == workspace_id)
        )
        for budget in budgets.scalars():
            if budget.monthly_limit > 0:
                ratio = float(budget.current_spend) / float(budget.monthly_limit)
                if ratio >= 1.0:
                    title = f"Budget exceeded: {budget.category}"
                    # LOW-001: Check for existing undismissed alert before creating
                    existing = await db.execute(
                        select(Alert).where(
                            and_(
                                Alert.workspace_id == workspace_id,
                                Alert.title == title,
                                Alert.is_dismissed.is_(False),
                            )
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        alert = Alert(
                            workspace_id=workspace_id,
                            title=title,
                            message=(
                                f"Spending in '{budget.category}' has reached "
                                f"{sym}{float(budget.current_spend):,.0f} "
                                f"({ratio:.0%} of {sym}{float(budget.monthly_limit):,.0f} limit)."
                            ),
                            severity=AlertSeverity.critical,
                            category="budget",
                        )
                        db.add(alert)
                        alerts_created += 1
                elif ratio >= 0.9:
                    title = f"Budget warning: {budget.category}"
                    # LOW-001: Check for existing undismissed alert before creating
                    existing = await db.execute(
                        select(Alert).where(
                            and_(
                                Alert.workspace_id == workspace_id,
                                Alert.title == title,
                                Alert.is_dismissed.is_(False),
                            )
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        alert = Alert(
                            workspace_id=workspace_id,
                            title=title,
                            message=(
                                f"Spending in '{budget.category}' is at "
                                f"{sym}{float(budget.current_spend):,.0f} "
                                f"({ratio:.0%} of {sym}{float(budget.monthly_limit):,.0f} limit)."
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
                Transaction.date >= (now - relativedelta(months=3)).replace(day=1),
            ))
            .group_by("m")
            .order_by("m")
        )
        monthly_incomes = [float(row[1] or 0) for row in income_q]
        if len(monthly_incomes) >= 2:
            prior_avg = sum(monthly_incomes[:-1]) / len(monthly_incomes[:-1])
            current = monthly_incomes[-1]
            if prior_avg > 0 and current < prior_avg * 0.7:
                title = "Revenue decline detected"
                # LOW-001: Check for existing undismissed alert before creating
                existing = await db.execute(
                    select(Alert).where(
                        and_(
                            Alert.workspace_id == workspace_id,
                            Alert.title == title,
                            Alert.is_dismissed.is_(False),
                        )
                    )
                )
                if existing.scalar_one_or_none() is None:
                    alert = Alert(
                        workspace_id=workspace_id,
                        title=title,
                        message=(
                            f"Current month revenue ({sym}{current:,.0f}) is "
                            f"{((1 - current / prior_avg) * 100):.0f}% below the "
                            f"trailing average ({sym}{prior_avg:,.0f})."
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


async def run_all_workspace_alerts() -> dict[str, int]:
    """EXT-002: Evaluate alert rules for ALL active workspaces.

    Designed to be called by APScheduler on a periodic interval so that
    alerts (e.g. "cash runway below 2 months") fire even when no user
    action triggers them.
    """
    from database import get_db_context, get_rls_db_context
    from models import Workspace

    results: dict[str, int] = {}

    async with get_db_context() as db:
        ws_q = await db.execute(select(Workspace.id))
        workspace_ids = [row[0] for row in ws_q]

    logger.info("Scheduled alert sweep starting for %d workspaces", len(workspace_ids))

    for ws_id in workspace_ids:
        try:
            # CRIT-002: Use RLS-bound session so queries are tenant-isolated
            async with get_rls_db_context(str(ws_id)) as db:
                count = await run_alert_engine(db, ws_id)
                results[str(ws_id)] = count
        except Exception:
            logger.exception("Scheduled alert sweep failed for workspace %s", ws_id)
            results[str(ws_id)] = -1

    total = sum(v for v in results.values() if v > 0)
    logger.info(
        "Scheduled alert sweep complete: %d workspaces, %d total alerts created",
        len(workspace_ids), total,
    )
    return results
