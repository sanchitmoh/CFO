"""
AI CFO — Chat Service
Intent-based context routing (ML-001) + data confidence scoring (ML-002).

Instead of fetching all financial context for every question,
we detect the user's intent and fetch only the relevant data slices.
"""
import re
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType, Budget


# ═══════════════════════════════════════════════════════════════════
# ML-001 — Intent-Based Context Router
# ═══════════════════════════════════════════════════════════════════

INTENT_MAP: dict[str, list[str]] = {
    r"runway|cash|afford|reserve|saving":         ["balance", "burn_rate", "cash_flow"],
    r"forecast|predict|future|project|trend":     ["time_series", "burn_rate"],
    r"budget|overspend|categor|limit|allocation":  ["budgets", "category_spend"],
    r"anomal|unusual|duplicate|weird|spike|outlier": ["flagged_transactions"],
    r"compar|benchmark|industry|kpi|metric":       ["benchmarks", "kpis"],
    r"revenue|income|earn|sale":                   ["revenue_detail", "cash_flow"],
    r"expense|spend|cost|bill|subscription":       ["category_spend", "burn_rate"],
}

DEFAULT_CONTEXTS = ["balance", "burn_rate", "category_spend"]


def detect_intent(question: str) -> list[str]:
    """Return context slices needed based on the user's question."""
    q = question.lower()
    matched: set[str] = set()
    for pattern, contexts in INTENT_MAP.items():
        if re.search(pattern, q):
            matched.update(contexts)
    return list(matched) if matched else DEFAULT_CONTEXTS


# ═══════════════════════════════════════════════════════════════════
# Context Fetchers — each returns a text block for the prompt
# ═══════════════════════════════════════════════════════════════════

async def _fetch_balance(db: AsyncSession, ws_id, cutoff: datetime) -> tuple[str, dict]:
    """Income/expense totals and net cash flow."""
    totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= cutoff))
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

    net = income - expenses
    text = (
        f"Total Income (90d): ${income:,.2f}\n"
        f"Total Expenses (90d): ${expenses:,.2f}\n"
        f"Net Cash Flow: ${net:,.2f}\n"
        f"Transaction Count: {txn_count}"
    )
    return text, {"income": income, "expenses": expenses, "txn_count": txn_count}


async def _fetch_burn_rate(db: AsyncSession, ws_id, cutoff: datetime) -> tuple[str, dict]:
    """Monthly burn rate and runway calculation."""
    result = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= cutoff))
        .group_by(Transaction.type)
    )
    income = 0.0
    expenses = 0.0
    for row in result:
        if row[0] == TransactionType.income:
            income = float(row[1] or 0)
        else:
            expenses = float(row[1] or 0)

    burn_rate = expenses / 3
    net = income - expenses
    runway = net / burn_rate if burn_rate > 0 else 99

    text = (
        f"Monthly Burn Rate: ${burn_rate:,.2f}\n"
        f"Estimated Runway: {runway:.1f} months"
    )
    return text, {"burn_rate": burn_rate, "runway": runway}


async def _fetch_category_spend(db: AsyncSession, ws_id, cutoff: datetime) -> tuple[str, dict]:
    """Top 5 expense categories."""
    cats_q = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(and_(
            Transaction.workspace_id == ws_id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= cutoff,
        ))
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    )
    lines = [f"  - {r[0]}: ${float(r[1]):,.2f}" for r in cats_q]
    text = "Top Expense Categories:\n" + ("\n".join(lines) if lines else "  No expense data")
    return text, {"category_count": len(lines)}


async def _fetch_cash_flow(db: AsyncSession, ws_id, cutoff: datetime) -> tuple[str, dict]:
    """Monthly cash flow trend."""
    from sqlalchemy import extract
    monthly = await db.execute(
        select(
            extract("year", Transaction.date).label("y"),
            extract("month", Transaction.date).label("m"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= cutoff))
        .group_by("y", "m", Transaction.type)
        .order_by("y", "m")
    )
    months_data: dict[str, dict] = {}
    for row in monthly:
        key = f"{int(row[0])}-{int(row[1]):02d}"
        if key not in months_data:
            months_data[key] = {"income": 0, "expenses": 0}
        if row[2] == TransactionType.income:
            months_data[key]["income"] = float(row[3] or 0)
        else:
            months_data[key]["expenses"] = float(row[3] or 0)

    lines = []
    for period in sorted(months_data.keys()):
        d = months_data[period]
        net = d["income"] - d["expenses"]
        lines.append(f"  {period}: Income ${d['income']:,.0f} | Expenses ${d['expenses']:,.0f} | Net ${net:,.0f}")

    text = "Monthly Cash Flow Trend:\n" + ("\n".join(lines) if lines else "  No data")
    return text, {"months_of_data": len(months_data)}


async def _fetch_budgets(db: AsyncSession, ws_id, _cutoff: datetime) -> tuple[str, dict]:
    """Budget adherence summary."""
    budgets_q = await db.execute(
        select(Budget).where(Budget.workspace_id == ws_id)
    )
    lines = []
    over_budget = 0
    for b in budgets_q.scalars():
        pct = float(b.current_spend) / float(b.monthly_limit) * 100 if b.monthly_limit > 0 else 0
        status = "OVER" if pct > 100 else "OK"
        if pct > 100:
            over_budget += 1
        lines.append(f"  - {b.category}: ${float(b.current_spend):,.0f} / ${float(b.monthly_limit):,.0f} ({pct:.0f}%) [{status}]")

    text = "Budget Status:\n" + ("\n".join(lines) if lines else "  No budgets configured")
    return text, {"budget_count": len(lines), "over_budget": over_budget}


async def _fetch_revenue_detail(db: AsyncSession, ws_id, cutoff: datetime) -> tuple[str, dict]:
    """Revenue breakdown by category."""
    rev_q = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(and_(
            Transaction.workspace_id == ws_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= cutoff,
        ))
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )
    lines = [f"  - {r[0]}: ${float(r[1]):,.2f} ({r[2]} transactions)" for r in rev_q]
    text = "Revenue Breakdown:\n" + ("\n".join(lines) if lines else "  No income data")
    return text, {"revenue_sources": len(lines)}


async def _fetch_flagged(db: AsyncSession, ws_id, _cutoff: datetime) -> tuple[str, dict]:
    """Recently flagged anomalies."""
    from models import Transaction as T
    flagged_q = await db.execute(
        select(T)
        .where(and_(T.workspace_id == ws_id, T.is_anomaly.is_(True)))
        .order_by(T.date.desc())
        .limit(5)
    )
    lines = [
        f"  - {t.date.strftime('%Y-%m-%d')}: {t.description} — ${float(t.amount):,.2f} (score: {t.anomaly_score:.1f})"
        for t in flagged_q.scalars()
    ]
    text = "Recent Anomalies:\n" + ("\n".join(lines) if lines else "  No anomalies flagged")
    return text, {"anomaly_count": len(lines)}


# Fetcher registry
CONTEXT_FETCHERS = {
    "balance":              _fetch_balance,
    "burn_rate":            _fetch_burn_rate,
    "category_spend":       _fetch_category_spend,
    "cash_flow":            _fetch_cash_flow,
    "time_series":          _fetch_cash_flow,   # alias
    "budgets":              _fetch_budgets,
    "revenue_detail":       _fetch_revenue_detail,
    "flagged_transactions": _fetch_flagged,
    "benchmarks":           _fetch_balance,      # fallback for now
    "kpis":                 _fetch_balance,      # fallback for now
}


async def build_context(
    db: AsyncSession, ws_id: uuid.UUID, question: str
) -> tuple[str, dict]:
    """
    Build financial context based on user intent.
    Returns (context_text, metadata_dict).

    ADVANCE-005: Also performs semantic search (RAG) to find the most
    relevant transactions for the user's question.
    """
    needed = detect_intent(question)
    cutoff = datetime.utcnow() - timedelta(days=90)

    sections: list[str] = []
    metadata: dict = {"intents": needed}
    seen_fetchers: set = set()

    for ctx_name in needed:
        fetcher = CONTEXT_FETCHERS.get(ctx_name)
        if fetcher and id(fetcher) not in seen_fetchers:
            seen_fetchers.add(id(fetcher))
            text, meta = await fetcher(db, ws_id, cutoff)
            sections.append(text)
            metadata.update(meta)

    # ── ADVANCE-005: Semantic RAG — find relevant transactions ────
    try:
        from services.embedding_service import get_relevant_transactions

        rag_results = await get_relevant_transactions(
            db, ws_id, question, top_k=5
        )
        if rag_results:
            rag_lines = []
            for row in rag_results:
                date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
                rag_lines.append(
                    f"  - {date_str}: {row.description} — "
                    f"${float(row.amount):,.2f} ({row.category}) "
                    f"[relevance: {float(row.similarity):.2f}]"
                )
            sections.append(
                "Relevant Transactions (semantic match):\n" + "\n".join(rag_lines)
            )
            metadata["rag_matches"] = len(rag_results)
    except Exception:
        # Semantic search is optional — degrade gracefully
        pass

    return "\n\n".join(sections), metadata


# ═══════════════════════════════════════════════════════════════════
# ML-002 — Data Confidence Scoring
# ═══════════════════════════════════════════════════════════════════

def compute_confidence(metadata: dict) -> tuple[str, str]:
    """
    Score data confidence based on available data quality.
    Returns (level, description_for_prompt).
    """
    txn_count = metadata.get("txn_count", 0)
    months = metadata.get("months_of_data", 0)

    # Estimate days of data from months, or from transaction count heuristic
    if months >= 3 or txn_count >= 50:
        return "high", ""
    elif months >= 1 or txn_count >= 10:
        return "medium", (
            f"Data confidence: MEDIUM — only {txn_count} transactions "
            f"across ~{months} month(s) of data. Note this limitation."
        )
    else:
        return "low", (
            f"Data confidence: LOW — only {txn_count} transactions available. "
            f"Acknowledge this limitation clearly in your response. "
            f"Preface uncertain projections with caveats."
        )
