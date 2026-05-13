"""
AI CFO - Reports router.
Generate financial summaries with date range filtering plus CSV and PDF export.
"""
import csv
import io
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from dependencies import get_rls_db
from models import Budget, Transaction, TransactionType, User, Workspace
from schemas import BudgetVarianceItem, CategorySummary, ReportSummary
from services.budget_service import normalize_category_key, normalize_category_label

router = APIRouter()

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


async def _get_workspace(db: AsyncSession, workspace_id) -> Workspace | None:
    return await db.scalar(select(Workspace).where(Workspace.id == workspace_id))


async def _get_report_data(
    db: AsyncSession,
    workspace_id,
    start: date,
    end: date,
) -> tuple[float, float, int, list[CategorySummary], list[dict]]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    totals = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .group_by(Transaction.type)
    )

    income = 0.0
    expenses = 0.0
    txn_count = 0
    for txn_type, amount, count in totals:
        if txn_type == TransactionType.income:
            income = float(amount or 0)
        else:
            expenses = float(amount or 0)
        txn_count += int(count or 0)

    categories = await db.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )

    expense_by_category = [
        CategorySummary(
            category=normalize_category_label(category or "Uncategorized"),
            total=float(total or 0),
            count=int(count or 0),
        )
        for category, total, count in categories
    ]

    vendors = await db.execute(
        select(
            Transaction.vendor,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
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
        {
            "vendor": vendor,
            "total": float(total or 0),
            "count": int(count or 0),
        }
        for vendor, total, count in vendors
    ]

    return income, expenses, txn_count, expense_by_category, top_vendors


def _resolve_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    end = end_date or datetime.now(timezone.utc).date()
    start = start_date or (end - timedelta(days=30))
    return start, end


def _iter_budget_months(start: date, end: date) -> list[str]:
    months: list[str] = []
    year = start.year
    month = start.month

    while (year, month) <= (end.year, end.month):
        months.append(f"{year}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return months


def _month_overlap_ratio(month_key: str, start: date, end: date) -> float:
    year, month = map(int, month_key.split("-"))
    days_in_month = monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)

    overlap_start = max(start, month_start)
    overlap_end = min(end, month_end)
    if overlap_start > overlap_end:
        return 0.0

    overlap_days = (overlap_end - overlap_start).days + 1
    return overlap_days / days_in_month


async def _get_budget_variance(
    db: AsyncSession,
    workspace_id,
    start: date,
    end: date,
    expense_by_category: list[CategorySummary],
) -> tuple[list[BudgetVarianceItem], float]:
    month_keys = _iter_budget_months(start, end)
    if not month_keys:
        return [], 0.0

    budgets = await db.execute(
        select(Budget.category, Budget.monthly_limit, Budget.month)
        .where(
            and_(
                Budget.workspace_id == workspace_id,
                Budget.month.in_(month_keys),
            )
        )
    )

    budget_totals: dict[str, dict[str, float | str]] = {}
    for category, monthly_limit, month_key in budgets:
        ratio = _month_overlap_ratio(month_key, start, end)
        if ratio <= 0:
            continue

        key = normalize_category_key(category)
        if key not in budget_totals:
            budget_totals[key] = {
                "category": normalize_category_label(category),
                "budget": 0.0,
            }
        budget_totals[key]["budget"] = float(budget_totals[key]["budget"]) + float(monthly_limit or 0) * ratio

    actual_totals = {
        normalize_category_key(item.category): item
        for item in expense_by_category
    }

    rows: list[BudgetVarianceItem] = []
    for key in set(actual_totals) | set(budget_totals):
        actual_item = actual_totals.get(key)
        budget_amount = round(float(budget_totals.get(key, {}).get("budget", 0.0)), 2)
        actual_amount = round(float(actual_item.total if actual_item else 0.0), 2)
        utilization_pct = (
            round((actual_amount / budget_amount) * 100, 1)
            if budget_amount > 0
            else (100.0 if actual_amount > 0 else 0.0)
        )

        rows.append(
            BudgetVarianceItem(
                category=str(
                    budget_totals.get(key, {}).get("category")
                    or (actual_item.category if actual_item else "Uncategorized")
                ),
                budget=budget_amount,
                actual=actual_amount,
                variance=round(actual_amount - budget_amount, 2),
                utilization_pct=utilization_pct,
                transaction_count=int(actual_item.count if actual_item else 0),
            )
        )

    rows.sort(key=lambda item: max(item.actual, item.budget), reverse=True)
    budget_total = round(sum(item.budget for item in rows), 2)
    return rows, budget_total


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Generate a financial summary report for the given period."""
    start, end = _resolve_dates(start_date, end_date)
    income, expenses, txn_count, expense_by_category, top_vendors = await _get_report_data(
        db, user.workspace_id, start, end
    )
    workspace = await _get_workspace(db, user.workspace_id)
    base_currency = (workspace.currency or "USD").upper() if workspace else "USD"
    budget_variance, budget_total = await _get_budget_variance(
        db, user.workspace_id, start, end, expense_by_category
    )

    return ReportSummary(
        period_start=start,
        period_end=end,
        base_currency=base_currency,
        total_income=income,
        total_expenses=expenses,
        net_cash_flow=income - expenses,
        transaction_count=txn_count,
        budget_total=budget_total,
        budget_variance=budget_variance,
        expense_by_category=expense_by_category,
        top_vendors=top_vendors,
    )


@router.get("/export/csv")
async def export_csv(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Export transactions as a downloadable CSV file."""
    start, end = _resolve_dates(start_date, end_date)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    workspace = await _get_workspace(db, user.workspace_id)
    base_currency = (workspace.currency or "USD").upper() if workspace else "USD"

    transactions = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.workspace_id == user.workspace_id,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .order_by(Transaction.date.desc())
    )

    async def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\r\n")

        yield "\ufeff"
        writer.writerow(
            [
                "Transaction Date",
                "Description",
                "Category",
                "Type",
                f"Amount ({base_currency})",
                "Workspace Currency",
                "Original Amount",
                "Original Currency",
                "Exchange Rate",
                "Vendor",
                "Account",
                "Source",
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for txn in transactions.scalars():
            writer.writerow(
                [
                    txn.date.strftime("%Y-%m-%d") if txn.date else "",
                    txn.description or "",
                    normalize_category_label(txn.category or "Uncategorized"),
                    txn.type.value if txn.type else "",
                    f"{float(txn.amount or 0):.2f}",
                    base_currency,
                    f"{float(txn.amount_original if txn.amount_original is not None else txn.amount or 0):.2f}",
                    (txn.currency_code or base_currency).upper(),
                    f"{float(txn.exchange_rate or 1):.6f}",
                    txn.vendor or "",
                    txn.account or "",
                    txn.source or "",
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"cfo_transactions_{base_currency.lower()}_{start}_{end}.csv"
    return StreamingResponse(
        _generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/pdf")
async def export_pdf(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Export a financial summary as a downloadable PDF report."""
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF export is not available. Install reportlab: pip install reportlab",
        )

    start, end = _resolve_dates(start_date, end_date)
    income, expenses, txn_count, expense_by_category, top_vendors = await _get_report_data(
        db, user.workspace_id, start, end
    )
    workspace = await _get_workspace(db, user.workspace_id)
    base_currency = (workspace.currency or "USD").upper() if workspace else "USD"
    workspace_name = workspace.name if workspace else "AI CFO Workspace"
    budget_variance, budget_total = await _get_budget_variance(
        db, user.workspace_id, start, end, expense_by_category
    )

    from services.alert_engine import get_currency_symbol

    symbol = get_currency_symbol(base_currency)
    net = income - expenses

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        spaceAfter=8,
        textColor=colors.HexColor("#101826"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#5C6675"),
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceAfter=8,
        textColor=colors.HexColor("#182334"),
    )
    footer_style = ParagraphStyle(
        "ReportFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6C7480"),
        alignment=1,
    )

    elements.append(Paragraph("Financial Report", title_style))
    elements.append(Paragraph(workspace_name, styles["Heading3"]))
    elements.append(
        Paragraph(
            (
                f"<b>Period:</b> {start} to {end} "
                f"&nbsp;&nbsp; <b>Base currency:</b> {base_currency} "
                f"&nbsp;&nbsp; <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            ),
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 0.22 * inch))

    elements.append(Paragraph("Executive Snapshot", section_style))
    summary_data = [
        ["Metric", "Amount"],
        ["Total Income", f"{symbol}{income:,.2f}"],
        ["Total Expenses", f"{symbol}{expenses:,.2f}"],
        ["Net Cash Flow", f"{symbol}{net:,.2f}"],
        ["Budgeted Spend", f"{symbol}{budget_total:,.2f}"],
        ["Transactions", f"{txn_count:,}"],
    ]
    summary_table = Table(summary_data, colWidths=[3.4 * inch, 2.2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#182334")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD1D8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F7F8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 0.24 * inch))

    if budget_variance:
        elements.append(Paragraph("Budget vs Actual", section_style))
        variance_data = [["Category", "Budget", "Actual", "Variance", "Use"]]
        for item in budget_variance[:10]:
            variance_data.append(
                [
                    item.category,
                    f"{symbol}{item.budget:,.2f}",
                    f"{symbol}{item.actual:,.2f}",
                    f"{symbol}{item.variance:,.2f}",
                    f"{item.utilization_pct:.0f}%",
                ]
            )

        variance_table = Table(
            variance_data,
            colWidths=[2.15 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch, 0.7 * inch],
        )
        variance_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C9A962")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#101826")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD1D8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFAF5")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(variance_table)
        elements.append(Spacer(1, 0.24 * inch))
    elif expense_by_category:
        elements.append(Paragraph("Expense Breakdown by Category", section_style))
        category_data = [["Category", "Actual Spend", "Transactions"]]
        for item in expense_by_category:
            category_data.append(
                [
                    item.category,
                    f"{symbol}{item.total:,.2f}",
                    str(item.count),
                ]
            )

        category_table = Table(category_data, colWidths=[2.7 * inch, 1.9 * inch, 1 * inch])
        category_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C9A962")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#101826")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD1D8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFAF5")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(category_table)
        elements.append(Spacer(1, 0.24 * inch))

    if top_vendors:
        elements.append(Paragraph("Top Vendors", section_style))
        vendor_data = [["Vendor", "Total", "Count"]]
        for vendor in top_vendors:
            vendor_data.append(
                [
                    vendor["vendor"],
                    f"{symbol}{vendor['total']:,.2f}",
                    str(vendor["count"]),
                ]
            )

        vendor_table = Table(vendor_data, colWidths=[2.5 * inch, 2 * inch, 1 * inch])
        vendor_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#355C7D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD1D8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F7F8")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(vendor_table)

    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph(
            "Generated by AI CFO. Amounts are shown in workspace currency unless otherwise noted.",
            footer_style,
        )
    )

    doc.build(elements)
    buf.seek(0)

    filename = f"cfo_report_{base_currency.lower()}_{start}_{end}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
