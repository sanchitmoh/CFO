"""
AI CFO — Chat Router
AI assistant with financial context from workspace data.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType, ChatMessage
from schemas import ChatRequest, ChatResponse
from config import settings

router = APIRouter()


async def _build_context(db: AsyncSession, ws_id: uuid.UUID) -> str:
    """Build financial context summary for the AI prompt."""
    cutoff = datetime.utcnow() - timedelta(days=90)

    totals = await db.execute(
        select(
            Transaction.type,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
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

    # Top 5 expense categories
    cats_q = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= cutoff,
            )
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    )
    top_cats = [f"  - {r[0]}: ${float(r[1]):,.2f}" for r in cats_q]

    net = income - expenses
    burn_rate = expenses / 3

    return f"""Financial Summary (Last 90 Days):
- Total Income: ${income:,.2f}
- Total Expenses: ${expenses:,.2f}
- Net Cash Flow: ${net:,.2f}
- Monthly Burn Rate: ${burn_rate:,.2f}
- Runway: {net/burn_rate:.1f} months (if burn stays constant)
- Transaction Count: {txn_count}
Top Expense Categories:
{chr(10).join(top_cats) if top_cats else '  No expense data available'}
"""


@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI CFO assistant."""
    session_id = req.session_id or str(uuid.uuid4())[:8]
    context = await _build_context(db, user.workspace_id)

    # ── Get conversation history (last 10 messages) ───────────────
    history_q = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.workspace_id == user.workspace_id,
                ChatMessage.session_id == session_id,
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history = list(reversed(list(history_q.scalars())))

    messages = [
        {
            "role": "system",
            "content": f"""You are an AI CFO assistant. You help small business owners understand 
their finances, make data-driven decisions, and optimize spending.

Here is the user's current financial data:
{context}

Be concise, specific, and actionable. Use the actual numbers above. 
If the user asks about data you don't have, say so honestly.""",
        }
    ]

    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    # ── Call OpenAI ────────────────────────────────────────────────
    try:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        completion = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
        )
        reply = completion.choices[0].message.content or "I couldn't generate a response."
        confidence = "high"
    except Exception as e:
        reply = (
            f"I'm temporarily unable to connect to the AI service. "
            f"Based on your data: your monthly burn rate is notable — "
            f"check your top expense categories for optimization opportunities."
        )
        confidence = "low"

    # ── Save messages ─────────────────────────────────────────────
    db.add(ChatMessage(
        workspace_id=user.workspace_id,
        user_id=user.id,
        session_id=session_id,
        role="user",
        content=req.message,
    ))
    db.add(ChatMessage(
        workspace_id=user.workspace_id,
        user_id=user.id,
        session_id=session_id,
        role="assistant",
        content=reply,
        confidence=confidence,
    ))
    await db.commit()

    return ChatResponse(
        reply=reply,
        sources=["Financial data from your workspace"],
        suggested_actions=[
            "View expense breakdown",
            "Check budget status",
            "Run a forecast",
        ],
        confidence=confidence,
    )


@router.get("/history")
async def chat_history(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.workspace_id == user.workspace_id,
                ChatMessage.session_id == session_id,
            )
        )
        .order_by(ChatMessage.created_at.asc())
    )
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in result.scalars()
    ]
