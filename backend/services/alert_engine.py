"""
Alert engine for in-app alerts plus optional email/Slack delivery.
"""
import logging
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Alert, AlertSeverity, Transaction, TransactionType, Workspace
from schemas import AlertSettingsOut
from services.budget_service import (
    get_budget_snapshots,
    normalize_category_key,
    normalize_category_label,
)
from services.email_service import email_service
from services.slack_service import slack_service

logger = logging.getLogger(__name__)


def get_currency_symbol(currency_code: str) -> str:
    symbols = {
        "USD": "$",
        "EUR": "EUR ",
        "GBP": "GBP ",
        "INR": "INR ",
        "JPY": "JPY ",
        "CAD": "CAD ",
        "AUD": "AUD ",
        "SGD": "SGD ",
        "CHF": "CHF ",
    }
    return symbols.get(currency_code.upper(), f"{currency_code.upper()} ")


def _load_alert_config(workspace: Workspace | None) -> AlertSettingsOut:
    defaults = AlertSettingsOut().model_dump()
    raw = workspace.alert_config if workspace and workspace.alert_config else {}
    return AlertSettingsOut(**{**defaults, **raw})


def _serialize_monthly_income(rows) -> list[tuple[str, float]]:
    series: list[tuple[str, float]] = []
    for year, month, total in rows:
        period = f"{int(year):04d}-{int(month):02d}"
        series.append((period, float(total or 0)))
    return series


def _revenue_drop_summary(
    monthly_income: list[tuple[str, float]],
) -> tuple[str, float, float] | None:
    if len(monthly_income) < 2:
        return None

    prior_periods = monthly_income[:-1][-3:]
    prior_avg = sum(amount for _, amount in prior_periods) / len(prior_periods)
    current_period, current_income = monthly_income[-1]

    if prior_avg <= 0 or current_income >= prior_avg * 0.7:
        return None

    return current_period, current_income, prior_avg


async def _alert_exists(
    db: AsyncSession,
    workspace_id,
    title: str,
    *,
    include_dismissed: bool = False,
) -> bool:
    filters = [
        Alert.workspace_id == workspace_id,
        Alert.title == title,
    ]
    if not include_dismissed:
        filters.append(Alert.is_dismissed.is_(False))

    result = await db.execute(select(Alert.id).where(and_(*filters)).limit(1))
    return result.scalar_one_or_none() is not None


async def _create_alert(
    db: AsyncSession,
    workspace_id,
    *,
    title: str,
    message: str,
    severity: AlertSeverity,
    category: str,
    created_alerts: list[dict],
    include_dismissed: bool = False,
) -> bool:
    if await _alert_exists(
        db,
        workspace_id,
        title,
        include_dismissed=include_dismissed,
    ):
        return False

    db.add(
        Alert(
            workspace_id=workspace_id,
            title=title,
            message=message,
            severity=severity,
            category=category,
        )
    )
    created_alerts.append(
        {
            "title": title,
            "message": message,
            "severity": severity.value,
            "category": category,
        }
    )
    return True


async def _dispatch_workspace_notifications(
    config: AlertSettingsOut,
    created_alerts: list[dict],
) -> None:
    recipients = [str(email) for email in config.email_addresses]

    for alert in created_alerts:
        if config.email_enabled and recipients:
            await email_service.send_alert_email(
                to_addresses=recipients,
                alert_title=alert["title"],
                alert_message=alert["message"],
                alert_severity=alert["severity"],
                alert_category=alert["category"],
            )

        if config.slack_enabled and config.slack_webhook_url:
            await slack_service.send_alert(
                title=alert["title"],
                message=alert["message"],
                severity=alert["severity"],
                category=alert["category"],
                webhook_url=config.slack_webhook_url,
            )


async def _compute_cash_balance(db: AsyncSession, workspace_id) -> float:
    totals = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(Transaction.workspace_id == workspace_id)
        .group_by(Transaction.type)
    )

    income = 0.0
    expenses = 0.0
    for txn_type, amount in totals:
        if txn_type == TransactionType.income:
            income = float(amount or 0)
        else:
            expenses = float(amount or 0)

    return round(income - expenses, 2)


async def run_alert_engine(db: AsyncSession, workspace_id) -> int:
    """
    Evaluate alert rules for a workspace and mirror new alerts to channels.

    Rules checked:
      1. Budget overrun (>= 90% warning, >= 100% critical)
      2. Low cash balance (workspace-configured threshold)
      3. Revenue decline (current month vs prior 3-month average)
      4. Unusual high expense (amount threshold + anomaly sensitivity)
    """
    now = datetime.now(timezone.utc)
    alerts_created = 0
    created_alerts: list[dict] = []

    try:
        workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
        currency = workspace.currency if workspace else "USD"
        sym = get_currency_symbol(currency)
        alert_config = _load_alert_config(workspace)

        for budget in await get_budget_snapshots(db, workspace_id):
            if budget.monthly_limit <= 0:
                continue

            ratio = budget.current_spend / budget.monthly_limit
            if ratio >= 1.0:
                created = await _create_alert(
                    db,
                    workspace_id,
                    title=f"Budget exceeded: {budget.category}",
                    message=(
                        f"Spending in '{budget.category}' has reached "
                        f"{sym}{budget.current_spend:,.0f} "
                        f"({ratio:.0%} of {sym}{budget.monthly_limit:,.0f} limit)."
                    ),
                    severity=AlertSeverity.critical,
                    category="budget",
                    created_alerts=created_alerts,
                )
                alerts_created += int(created)
            elif ratio >= 0.9:
                created = await _create_alert(
                    db,
                    workspace_id,
                    title=f"Budget warning: {budget.category}",
                    message=(
                        f"Spending in '{budget.category}' is at "
                        f"{sym}{budget.current_spend:,.0f} "
                        f"({ratio:.0%} of {sym}{budget.monthly_limit:,.0f} limit)."
                    ),
                    severity=AlertSeverity.warning,
                    category="budget",
                    created_alerts=created_alerts,
                )
                alerts_created += int(created)

        cash_balance = await _compute_cash_balance(db, workspace_id)
        if cash_balance <= alert_config.low_cash_threshold:
            created = await _create_alert(
                db,
                workspace_id,
                title="Low cash balance",
                message=(
                    f"Estimated cash balance is {sym}{cash_balance:,.0f}, "
                    f"below the configured threshold of "
                    f"{sym}{alert_config.low_cash_threshold:,.0f}."
                ),
                severity=AlertSeverity.critical,
                category="cash",
                created_alerts=created_alerts,
            )
            alerts_created += int(created)

        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue_rows = await db.execute(
            select(
                func.extract("year", Transaction.date).label("year"),
                func.extract("month", Transaction.date).label("month"),
                func.sum(Transaction.amount).label("total"),
            )
            .where(
                and_(
                    Transaction.workspace_id == workspace_id,
                    Transaction.type == TransactionType.income,
                    Transaction.date >= current_month_start - relativedelta(months=3),
                )
            )
            .group_by("year", "month")
            .order_by("year", "month")
        )
        monthly_income = _serialize_monthly_income(revenue_rows)
        revenue_decline = _revenue_drop_summary(monthly_income)
        if revenue_decline:
            current_period, current_income, prior_avg = revenue_decline
            drop_pct = (1 - (current_income / prior_avg)) * 100
            created = await _create_alert(
                db,
                workspace_id,
                title="Revenue decline detected",
                message=(
                    f"{current_period} revenue ({sym}{current_income:,.0f}) is "
                    f"{drop_pct:.0f}% below the trailing average "
                    f"({sym}{prior_avg:,.0f})."
                ),
                severity=AlertSeverity.warning,
                category="revenue",
                created_alerts=created_alerts,
            )
            alerts_created += int(created)

        baseline_rows = await db.execute(
            select(
                Transaction.category,
                func.avg(Transaction.amount).label("average_amount"),
            )
            .where(
                and_(
                    Transaction.workspace_id == workspace_id,
                    Transaction.type == TransactionType.expense,
                    Transaction.date >= now - relativedelta(months=6),
                )
            )
            .group_by(Transaction.category)
        )
        category_averages = {
            normalize_category_key(category or "Uncategorized"): float(average_amount or 0)
            for category, average_amount in baseline_rows
        }

        candidate_rows = await db.execute(
            select(
                Transaction.date,
                Transaction.description,
                Transaction.category,
                Transaction.amount,
            )
            .where(
                and_(
                    Transaction.workspace_id == workspace_id,
                    Transaction.type == TransactionType.expense,
                    Transaction.amount >= alert_config.high_expense_threshold,
                    Transaction.date >= now - relativedelta(days=45),
                )
            )
            .order_by(Transaction.date.desc())
        )

        for txn_date, description, category, amount in candidate_rows:
            category_label = normalize_category_label(category or "Uncategorized")
            baseline = category_averages.get(normalize_category_key(category_label), 0.0)
            amount_value = float(amount or 0)
            if baseline <= 0:
                continue
            if amount_value < baseline * alert_config.anomaly_sensitivity:
                continue

            descriptor = (description or category_label or "Expense").strip()
            title = f"Unusual expense detected: {descriptor[:32]} ({txn_date:%Y-%m-%d})"
            created = await _create_alert(
                db,
                workspace_id,
                title=title,
                message=(
                    f"{sym}{amount_value:,.0f} spent on '{category_label}' is "
                    f"{amount_value / baseline:.1f}x the recent category average "
                    f"of {sym}{baseline:,.0f}."
                ),
                severity=AlertSeverity.warning,
                category="expense",
                created_alerts=created_alerts,
                include_dismissed=True,
            )
            alerts_created += int(created)

        if created_alerts:
            await db.commit()
            await _dispatch_workspace_notifications(alert_config, created_alerts)

        logger.info(
            "Alert engine completed for workspace %s: %d alerts created",
            workspace_id,
            alerts_created,
        )
    except Exception:
        logger.exception("Alert engine failed for workspace %s", workspace_id)
        await db.rollback()

    return alerts_created


async def run_all_workspace_alerts() -> dict[str, int]:
    """Evaluate alert rules for all workspaces with tenant-isolated sessions."""
    from database import get_db_context, get_rls_db_context
    from models import Workspace

    results: dict[str, int] = {}

    async with get_db_context() as db:
        ws_q = await db.execute(select(Workspace.id))
        workspace_ids = [row[0] for row in ws_q]

    logger.info("Scheduled alert sweep starting for %d workspaces", len(workspace_ids))

    for ws_id in workspace_ids:
        try:
            async with get_rls_db_context(str(ws_id)) as db:
                count = await run_alert_engine(db, ws_id)
                results[str(ws_id)] = count
        except Exception:
            logger.exception("Scheduled alert sweep failed for workspace %s", ws_id)
            results[str(ws_id)] = -1

    total = sum(value for value in results.values() if value > 0)
    logger.info(
        "Scheduled alert sweep complete: %d workspaces, %d total alerts created",
        len(workspace_ids),
        total,
    )
    return results
