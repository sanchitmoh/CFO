"""
AI CFO — Chat Service
Intent-based context routing (ML-001) + data confidence scoring (ML-002).

Instead of fetching all financial context for every question,
we detect the user's intent and fetch only the relevant data slices.
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType
from services.budget_service import get_budget_snapshots


# ═══════════════════════════════════════════════════════════════════
# SEC-001 — Input / Output Sanitization
# ═══════════════════════════════════════════════════════════════════

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
# SEC-FIX: Enhanced prompt delimiter detection including Unicode variants
_PROMPT_DELIMITERS_RE = re.compile(
    r"(───|═══|\*\*\*|###|```|<<|>>|\{\{|\}\}|"
    r"\u2500+|\u2501+|\u2550+|"  # Unicode box drawing
    r"SYSTEM:|ASSISTANT:|USER:|"  # Role confusion attempts
    r"Ignore previous|ignore all|disregard|new instructions)",
    re.IGNORECASE
)

MAX_INPUT_LENGTH = 2000


def sanitize_input(text: str) -> str:
    """Sanitize user input before intent detection or prompt construction.

    Strips control characters, HTML tags, and common prompt-injection
    delimiters to prevent the user from escaping the financial-data
    sandbox in the system prompt.
    
    SEC-FIX: Enhanced to detect Unicode normalization attacks and role confusion.
    """
    if not text:
        return ""
    
    # Normalize Unicode to prevent homoglyph attacks
    import unicodedata
    text = unicodedata.normalize("NFKC", text)
    
    text = text[:MAX_INPUT_LENGTH]
    text = _CONTROL_CHAR_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    text = _PROMPT_DELIMITERS_RE.sub("", text)
    
    # Remove multiple newlines that could be used for prompt breaking
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()


def sanitize_data_field(value: str, max_len: int = 200) -> str:
    """Sanitize database-sourced strings before injecting into AI prompts.

    Transaction descriptions and categories come from bank feeds or
    user uploads. A malicious actor could craft a CSV with payloads
    like '<script>alert(1)</script>' or '─── END FINANCIAL DATA ───'
    to break out of the prompt sandbox.
    """
    if not value:
        return ""
    value = str(value)[:max_len]
    value = _CONTROL_CHAR_RE.sub("", value)
    value = _HTML_TAG_RE.sub("", value)
    value = _PROMPT_DELIMITERS_RE.sub("", value)
    return value.strip()


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
CONTEXT_WINDOW_DAYS = 90


def detect_intent(question: str) -> list[str]:
    """Return context slices needed based on the user's question."""
    q = sanitize_input(question).lower()
    matched: set[str] = set()
    for pattern, contexts in INTENT_MAP.items():
        if re.search(pattern, q):
            matched.update(contexts)
    return list(matched) if matched else DEFAULT_CONTEXTS


# ═══════════════════════════════════════════════════════════════════
# Context Fetchers — each returns a text block for the prompt
# ═══════════════════════════════════════════════════════════════════

async def _fetch_transaction_totals(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    query_cache: dict | None = None,
) -> dict[str, float | int]:
    """Fetch 90-day transaction totals once and reuse them across contexts."""
    cache_key = ("transaction_totals", ws_id, cutoff)
    if query_cache is not None and cache_key in query_cache:
        return query_cache[cache_key]

    totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= cutoff))
        .group_by(Transaction.type)
    )
    summary = {"income": 0.0, "expenses": 0.0, "txn_count": 0}
    for row in totals:
        if row[0] == TransactionType.income:
            summary["income"] = float(row[1] or 0)
        else:
            summary["expenses"] = float(row[1] or 0)
        summary["txn_count"] += int(row[2] or 0)

    if query_cache is not None:
        query_cache[cache_key] = summary
    return summary


def _format_window_label(query_cache: dict | None) -> str:
    """Return a human-readable date range for the active context window."""
    if not query_cache:
        return f"last {CONTEXT_WINDOW_DAYS} days"
    window_start = query_cache.get("window_start")
    window_end = query_cache.get("window_end")
    if window_start and window_end:
        return f"{window_start} to {window_end}"
    return f"last {CONTEXT_WINDOW_DAYS} days"


def resolve_context_window(
    latest_transaction_at: datetime | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime, int]:
    """Choose the best analysis window for current or stale workspaces."""
    current_time = now or datetime.now(timezone.utc)
    current_cutoff = current_time - timedelta(days=CONTEXT_WINDOW_DAYS)

    if latest_transaction_at and latest_transaction_at < current_cutoff:
        window_end = latest_transaction_at
        window_start = latest_transaction_at - timedelta(days=CONTEXT_WINDOW_DAYS)
    else:
        window_end = current_time
        window_start = current_cutoff

    stale_days = (
        max((current_time.date() - latest_transaction_at.date()).days, 0)
        if latest_transaction_at
        else 0
    )
    return window_start, window_end, stale_days


async def _fetch_balance(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    sym: str,
    query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Income/expense totals and net cash flow."""
    summary = await _fetch_transaction_totals(db, ws_id, cutoff, query_cache)
    income = float(summary["income"])
    expenses = float(summary["expenses"])
    txn_count = int(summary["txn_count"])
    window_label = _format_window_label(query_cache)

    net = income - expenses
    text = (
        f"Total Income ({window_label}): {sym}{income:,.2f}\n"
        f"Total Expenses ({window_label}): {sym}{expenses:,.2f}\n"
        f"Net Cash Flow: {sym}{net:,.2f}\n"
        f"Transaction Count: {txn_count}"
    )
    return text, {"income": income, "expenses": expenses, "txn_count": txn_count}


async def _fetch_burn_rate(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    sym: str,
    query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Monthly burn rate and runway calculation."""
    summary = await _fetch_transaction_totals(db, ws_id, cutoff, query_cache)
    income = float(summary["income"])
    expenses = float(summary["expenses"])
    window_label = _format_window_label(query_cache)

    burn_rate = expenses / 3
    net = income - expenses
    runway = net / burn_rate if burn_rate > 0 else 99

    text = (
        f"Monthly Burn Rate ({window_label}): {sym}{burn_rate:,.2f}\n"
        f"Estimated Runway: {runway:.1f} months"
    )
    return text, {"burn_rate": burn_rate, "runway": runway}


async def _fetch_category_spend(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    sym: str,
    _query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Top 5 expense categories."""
    window_label = _format_window_label(_query_cache)
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
    lines = [f"  - {sanitize_data_field(r[0])}: {sym}{float(r[1]):,.2f}" for r in cats_q]
    text = f"Top Expense Categories ({window_label}):\n" + ("\n".join(lines) if lines else "  No expense data")
    return text, {"category_count": len(lines)}


async def _fetch_cash_flow(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    sym: str,
    _query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Monthly cash flow trend."""
    from sqlalchemy import extract
    window_label = _format_window_label(_query_cache)
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
        lines.append(f"  {period}: Income {sym}{d['income']:,.0f} | Expenses {sym}{d['expenses']:,.0f} | Net {sym}{net:,.0f}")

    text = f"Monthly Cash Flow Trend ({window_label}):\n" + ("\n".join(lines) if lines else "  No data")
    return text, {"months_of_data": len(months_data)}


async def _fetch_budgets(
    db: AsyncSession,
    ws_id,
    _cutoff: datetime,
    sym: str,
    _query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Budget adherence summary."""
    lines = []
    over_budget = 0
    for budget in await get_budget_snapshots(db, ws_id):
        pct = budget.percentage_used
        status = "OVER" if budget.status == "over_budget" else "OK"
        if budget.status == "warning":
            status = "WARNING"
        if pct > 100:
            over_budget += 1
        lines.append(
            f"  - {sanitize_data_field(budget.category)}: "
            f"{sym}{budget.current_spend:,.0f} / {sym}{budget.monthly_limit:,.0f} "
            f"({pct:.0f}%) [{status}]"
        )

    text = "Budget Status:\n" + ("\n".join(lines) if lines else "  No budgets configured")
    return text, {"budget_count": len(lines), "over_budget": over_budget}


async def _fetch_revenue_detail(
    db: AsyncSession,
    ws_id,
    cutoff: datetime,
    sym: str,
    _query_cache: dict | None = None,
) -> tuple[str, dict]:
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
    lines = [f"  - {sanitize_data_field(r[0])}: {sym}{float(r[1]):,.2f} ({r[2]} transactions)" for r in rev_q]
    text = "Revenue Breakdown:\n" + ("\n".join(lines) if lines else "  No income data")
    return text, {"revenue_sources": len(lines)}


async def _fetch_flagged(
    db: AsyncSession,
    ws_id,
    _cutoff: datetime,
    sym: str,
    _query_cache: dict | None = None,
) -> tuple[str, dict]:
    """Recently flagged anomalies."""
    from models import Transaction as T
    flagged_q = await db.execute(
        select(T)
        .where(and_(T.workspace_id == ws_id, T.is_anomaly.is_(True)))
        .order_by(T.date.desc())
        .limit(5)
    )
    lines = [
        f"  - {t.date.strftime('%Y-%m-%d')}: {sanitize_data_field(t.description)} — {sym}{float(t.amount):,.2f} (score: {t.anomaly_score:.1f})"
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
    safe_question = sanitize_input(question)

    sections: list[str] = []
    metadata: dict = {"intents": needed}
    seen_fetchers: set = set()
    query_cache: dict = {}

    from models import Workspace
    from services.alert_engine import get_currency_symbol
    ws = await db.scalar(select(Workspace).where(Workspace.id == ws_id))
    sym = get_currency_symbol(ws.currency if ws else "USD")
    latest_transaction_at = await db.scalar(
        select(func.max(Transaction.date)).where(Transaction.workspace_id == ws_id)
    )
    cutoff, window_end, stale_days = resolve_context_window(latest_transaction_at)
    metadata.update({
        "window_start": cutoff.date().isoformat(),
        "window_end": window_end.date().isoformat(),
        "stale_days": stale_days,
    })
    if latest_transaction_at is not None:
        metadata["latest_transaction_at"] = latest_transaction_at.isoformat()
    query_cache.update({
        "window_start": cutoff.date().isoformat(),
        "window_end": window_end.date().isoformat(),
    })

    for ctx_name in needed:
        fetcher = CONTEXT_FETCHERS.get(ctx_name)
        if fetcher and id(fetcher) not in seen_fetchers:
            seen_fetchers.add(id(fetcher))
            text, meta = await fetcher(db, ws_id, cutoff, sym, query_cache)
            sections.append(text)
            metadata.update(meta)

    # ── ADVANCE-005: Semantic RAG — find relevant transactions ────
    try:
        from services.embedding_service import get_relevant_transactions

        rag_results = await get_relevant_transactions(
            db, ws_id, safe_question, top_k=5
        )
        if rag_results:
            rag_lines = []
            for row in rag_results:
                date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
                rag_lines.append(
                    f"  - {date_str}: {sanitize_data_field(row.description)} — "
                    f"{sym}{float(row.amount):,.2f} ({sanitize_data_field(row.category)}) "
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
    stale_days = metadata.get("stale_days", 0)
    window_end = metadata.get("window_end")

    # Estimate days of data from months, or from transaction count heuristic
    if months >= 3 or txn_count >= 50:
        level = "high"
        note = ""
    elif months >= 1 or txn_count >= 10:
        level = "medium"
        note = (
            f"Data confidence: MEDIUM — only {txn_count} transactions "
            f"across ~{months} month(s) of data. Note this limitation."
        )
    else:
        level = "low"
        note = (
            f"Data confidence: LOW — only {txn_count} transactions available. "
            f"Acknowledge this limitation clearly in your response. "
            f"Preface uncertain projections with caveats."
        )

    if stale_days >= 365:
        level = "low"
        note = (
            f"Data confidence: LOW — the latest transaction data ends on {window_end} "
            f"and is {stale_days} days old. Answer using historical context only, not as current status."
        )
    elif stale_days >= 90:
        if level == "high":
            level = "medium"
        note = (
            f"Data recency warning: latest transaction data ends on {window_end} "
            f"and is {stale_days} days old. Be explicit that this is a historical summary."
        )

    return level, note


# ═══════════════════════════════════════════════════════════════════
# ML-003 — Token Management & History Compression
# ═══════════════════════════════════════════════════════════════════

MAX_HISTORY_MESSAGES = 10
MAX_CONTEXT_TOKENS = 4000


def estimate_tokens(text: str) -> int:
    """Rough token estimation (~4 chars per token for English)."""
    return len(text) // 4


def compress_history(
    messages: list[dict[str, str]],
    max_messages: int = MAX_HISTORY_MESSAGES,
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> list[dict[str, str]]:
    """Sliding window with summarization for chat history.

    Keeps the most recent `max_messages` messages. If the total token
    count still exceeds `max_tokens`, summarize the older messages
    into a single system message and keep the last 4 verbatim.
    """
    if not messages:
        return []

    # Step 1: Sliding window — keep last N messages
    trimmed = messages[-max_messages:]

    # Step 2: Check token budget
    total = sum(estimate_tokens(m.get("content", "")) for m in trimmed)
    if total <= max_tokens:
        return trimmed

    # Step 3: Summarize older messages, keep last 4 verbatim
    if len(trimmed) <= 4:
        return trimmed

    older = trimmed[:-4]
    recent = trimmed[-4:]

    # Build a condensed summary of the older exchange
    summary_parts = []
    for m in older:
        role = m.get("role", "user")
        content = m.get("content", "")
        # Truncate each message to a reasonable length
        snippet = content[:200] + "..." if len(content) > 200 else content
        summary_parts.append(f"[{role}]: {snippet}")

    summary_text = "\n".join(summary_parts)
    summary_msg = {
        "role": "system",
        "content": (
            f"[Earlier conversation summary — {len(older)} messages condensed]:\n"
            f"{summary_text}"
        ),
    }

    return [summary_msg] + recent


# ═══════════════════════════════════════════════════════════════════
# ML-004 — Hardened System Prompt Builder
# ═══════════════════════════════════════════════════════════════════

def build_system_prompt(
    context: str,
    confidence_level: str,
    confidence_note: str,
    metadata: dict,
) -> str:
    """Build a grounded, confidence-aware system prompt with guardrails.

    Unlike the old static prompt, this version:
    - Injects data confidence levels
    - Requires citation of data points
    - Adds explicit hallucination guards
    - Labels forecast confidence by time horizon
    - Includes financial disclaimer
    """
    txn_count = metadata.get("txn_count", 0)
    months = metadata.get("months_of_data", 0)
    intents = metadata.get("intents", [])
    rag_matches = metadata.get("rag_matches", 0)
    window_start = metadata.get("window_start", "unknown")
    window_end = metadata.get("window_end", "unknown")
    stale_days = metadata.get("stale_days", 0)

    data_days = months * 30 if months else max(txn_count // 2, 1)

    low_data_warning = ""
    if data_days < 30:
        low_data_warning = (
            "\n⚠️ WARNING: Less than 30 days of data available. "
            "Answers may be unreliable. State this clearly.\n"
        )
    if stale_days >= 90:
        low_data_warning += (
            f"\n⚠️ RECENCY WARNING: The latest transaction data ends on {window_end} "
            f"and is {stale_days} days old. Treat this as historical data, not current performance.\n"
        )

    return f"""You are an AI CFO assistant for a small business. You help owners understand their finances, make data-driven decisions, and optimize spending.

RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION:
1. NEVER invent or guess numbers. If the data below doesn't contain the answer, say exactly: "I don't have enough data to answer this accurately."
2. ALWAYS cite which data point you used. Example: "Based on your 90-day income of $X..."
3. For projections beyond 3 months, prefix with: "This is a low-confidence estimate based on limited history."
4. You are NOT a licensed financial advisor. If giving strategic advice, add: "Consider consulting a qualified financial advisor for major decisions."
5. When comparing periods, state the exact date ranges being compared.
6. If asked about data you don't have (e.g., individual invoices, payroll details), say so explicitly rather than making assumptions.
7. The chat UI renders plain text, so DO NOT use markdown tables, code fences, or decorative markup. Prefer clean headings and simple bullet lists.
8. For ranked summaries like biggest expenses, use this structure when data exists:
   Summary:
   <one-sentence takeaway>
   Period:
   <exact date range>
   Top items:
   - <item>: <amount>
   Recommendations:
   - <action tied to the largest category>
   - <second practical action>
9. When the user asks for spending or expense summaries, include 2-3 concrete recommendations grounded in the largest categories shown in the data.

DATA CONFIDENCE: {confidence_level.upper()} ({data_days} days of transaction history, {txn_count} transactions)
{confidence_note}
{low_data_warning}
DATA WINDOW: {window_start} to {window_end}
CONTEXT RETRIEVED FOR: {', '.join(intents) if intents else 'general overview'}
SEMANTIC MATCHES: {rag_matches} relevant transactions found

─── FINANCIAL DATA ───
{context}
─── END FINANCIAL DATA ───

Respond concisely and use the actual numbers above. Format currency values consistently. Use bullet points for clarity when listing multiple items."""
