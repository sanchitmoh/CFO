"""
AI CFO — Reports Router
Generate financial reports with date range filtering, CSV & PDF export.
"""
import csv
import io
from datetime import datetime, timedelta, date, timezone

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Transaction, TransactionType
from schemas import ReportSummary, CategorySummary

router = APIRouter()

# MED-008: Import reportlab at module level with graceful fallback
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════
# Helper: shared query logic for date-ranged report data
# ═══════════════════════════════════════════════════════════════════

async def _get_report_data(
    db: AsyncSession,
    ws_id,
    start: date,
    end: date,
):
    """Return (income, expenses, txn_count, expense_by_cat, top_vendors, transactions)."""
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

    # MED-007: Return query result instead of materializing all transactions
    # into memory. Caller can iterate over the result for true streaming.
    txn_q = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
        )
        .order_by(Transaction.date.desc())
    )

    return income, expenses, txn_count, expense_by_cat, top_vendors, txn_q


def _resolve_dates(start_date: date | None, end_date: date | None):
    # MED-005: Use UTC instead of server-local timezone for consistent
    # report date boundaries regardless of deployment region.
    end = end_date or datetime.now(timezone.utc).date()
    start = start_date or (end - timedelta(days=30))
    return start, end


# ═══════════════════════════════════════════════════════════════════
# GET /summary — JSON report
# ═══════════════════════════════════════════════════════════════════

@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Generate a financial summary report for the given period."""
    start, end = _resolve_dates(start_date, end_date)
    # MED-007: Don't need transactions for summary, pass None
    income, expenses, txn_count, expense_by_cat, top_vendors, txn_q = await _get_report_data(
        db, user.workspace_id, start, end
    )

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


# ═══════════════════════════════════════════════════════════════════
# GET /export/csv — Download transactions as CSV (FILE-002)
# ═══════════════════════════════════════════════════════════════════

@router.get("/export/csv")
async def export_csv(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Export transactions as a downloadable CSV file.
    
    MED-007: Uses true streaming via async generator to avoid loading
    all transactions into memory. For workspaces with 500K+ transactions,
    this prevents OOM errors.
    """
    start, end = _resolve_dates(start_date, end_date)
    _, _, _, _, _, txn_q = await _get_report_data(
        db, user.workspace_id, start, end
    )

    async def _generate():
        """MED-007: True streaming generator - yields rows as they're fetched."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        
        # Write header
        writer.writerow(["Date", "Description", "Category", "Type", "Amount", "Vendor", "Account", "Source"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        # Stream rows from database result
        for txn in txn_q.scalars():
            writer.writerow([
                txn.date.strftime("%Y-%m-%d") if txn.date else "",
                txn.description or "",
                txn.category or "",
                txn.type.value if txn.type else "",
                f"{float(txn.amount):.2f}",
                txn.vendor or "",
                txn.account or "",
                txn.source or "",
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"cfo_transactions_{start}_{end}.csv"
    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════
# GET /export/pdf — Download financial summary as PDF (FILE-002)
# ═══════════════════════════════════════════════════════════════════

@router.get("/export/pdf")
async def export_pdf(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Export a financial summary as a downloadable PDF report.
    
    MED-008: Requires reportlab package. Returns 501 if not installed.
    """
    # MED-008: Check if reportlab is available at request time
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="PDF export is not available. Install reportlab: pip install reportlab",
        )
    
    start, end = _resolve_dates(start_date, end_date)
    income, expenses, txn_count, expense_by_cat, top_vendors, _ = await _get_report_data(
        db, user.workspace_id, start, end
    )

    # ── Build PDF in memory ───────────────────────────────────────

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    )
    elements.append(Paragraph("AI CFO — Financial Report", title_style))
    elements.append(Paragraph(
        f"<b>Period:</b> {start} to {end}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # ── Summary table ─────────────────────────────────────────────
    net = income - expenses
    summary_data = [
        ["Metric", "Amount"],
        ["Total Income", f"${income:,.2f}"],
        ["Total Expenses", f"${expenses:,.2f}"],
        ["Net Cash Flow", f"${net:,.2f}"],
        ["Transactions", f"{txn_count:,}"],
    ]
    summary_table = Table(summary_data, colWidths=[3 * inch, 2.5 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ── Expense by category table ─────────────────────────────────
    if expense_by_cat:
        elements.append(Paragraph("Expense Breakdown by Category", styles["Heading2"]))
        cat_data = [["Category", "Total", "Count"]]
        for cat in expense_by_cat:
            cat_data.append([cat.category, f"${cat.total:,.2f}", str(cat.count)])

        cat_table = Table(cat_data, colWidths=[2.5 * inch, 2 * inch, 1 * inch])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 0.3 * inch))

    # ── Top vendors table ─────────────────────────────────────────
    if top_vendors:
        elements.append(Paragraph("Top Vendors", styles["Heading2"]))
        vendor_data = [["Vendor", "Total", "Count"]]
        for v in top_vendors:
            vendor_data.append([v["vendor"], f"${v['total']:,.2f}", str(v["count"])])

        vendor_table = Table(vendor_data, colWidths=[2.5 * inch, 2 * inch, 1 * inch])
        vendor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#533483")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(vendor_table)

    # ── Footer ────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5 * inch))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontSize=8,
        textColor=colors.grey, alignment=1,
    )
    elements.append(Paragraph(
        f"Generated by AI CFO on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        footer_style,
    ))

    doc.build(elements)
    buf.seek(0)

    filename = f"cfo_report_{start}_{end}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
