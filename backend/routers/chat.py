"""
AI CFO — Chat Router
AI assistant with financial context from workspace data.
Sessions are UUID-identified, workspace-scoped, and user-owned.
Includes both blocking and streaming (SSE) endpoints.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import openai

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType, ChatMessage, ChatSession
from schemas import ChatRequest, ChatResponse, ChatSessionOut
from config import settings
from telemetry import openai_traced

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────


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
    burn_rate = expenses / 3 if expenses else 0

    # ── Semantic RAG context (ADVANCE-005) ────────────────────────
    rag_context = ""
    try:
        from services.embedding_service import get_relevant_transactions
        relevant = await get_relevant_transactions(
            db, ws_id, "recent financial activity summary", top_k=5
        )
        if relevant:
            rag_lines = [f"  - {t.description}: ${float(t.amount):,.2f} ({t.category})" for t in relevant]
            rag_context = f"\nSemanticly Relevant Transactions:\n{chr(10).join(rag_lines)}\n"
    except Exception:
        pass  # Embedding service not available — degrade gracefully

    return f"""Financial Summary (Last 90 Days):
- Total Income: ${income:,.2f}
- Total Expenses: ${expenses:,.2f}
- Net Cash Flow: ${net:,.2f}
- Monthly Burn Rate: ${burn_rate:,.2f}
- Runway: {net / burn_rate:.1f} months (if burn stays constant)
- Transaction Count: {txn_count}
Top Expense Categories:
{chr(10).join(top_cats) if top_cats else '  No expense data available'}
{rag_context}"""


async def _get_or_create_session(
    db: AsyncSession,
    user: User,
    session_id: Optional[uuid.UUID],
) -> ChatSession:
    """Resolve an existing session or create a new one.

    If session_id is provided, verify it belongs to the user's workspace.
    If not provided, create a fresh session.
    """
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.workspace_id == user.workspace_id,
                )
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found or does not belong to this workspace.",
            )
        return session

    # Create new session
    session = ChatSession(
        workspace_id=user.workspace_id,
        user_id=user.id,
    )
    db.add(session)
    await db.flush()  # assigns session.id
    return session


def _build_system_prompt(context: str) -> str:
    """Build the system prompt with financial context."""
    return f"""You are an AI CFO assistant. You help small business owners understand 
their finances, make data-driven decisions, and optimize spending.

Here is the user's current financial data:
{context}

Be concise, specific, and actionable. Use the actual numbers above. 
If the user asks about data you don't have, say so honestly."""


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI CFO assistant."""
    session = await _get_or_create_session(db, user, req.session_id)
    context = await _build_context(db, user.workspace_id)

    # ── Get conversation history (last 10 messages) ───────────────
    history_q = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.workspace_id == user.workspace_id,
                ChatMessage.session_id == session.id,
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history = list(reversed(list(history_q.scalars())))

    messages = [{"role": "system", "content": _build_system_prompt(context)}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    # ── Call OpenAI (with custom tracing) ──────────────────────────
    try:
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        async with openai_traced(model=settings.OPENAI_MODEL, stream=False) as span:
            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800,
            )
            reply = completion.choices[0].message.content or "I couldn't generate a response."
            confidence = "high"

            # Record token usage in the trace span
            if span and completion.usage:
                span.set_attribute("ai.tokens.prompt", completion.usage.prompt_tokens)
                span.set_attribute("ai.tokens.completion", completion.usage.completion_tokens)
                span.set_attribute("ai.tokens.total", completion.usage.total_tokens)

    except Exception:
        reply = (
            "I'm temporarily unable to connect to the AI service. "
            "Based on your data: your monthly burn rate is notable — "
            "check your top expense categories for optimization opportunities."
        )
        confidence = "low"

    # ── Save messages ─────────────────────────────────────────────
    db.add(ChatMessage(
        workspace_id=user.workspace_id,
        user_id=user.id,
        session_id=session.id,
        role="user",
        content=req.message,
    ))
    db.add(ChatMessage(
        workspace_id=user.workspace_id,
        user_id=user.id,
        session_id=session.id,
        role="assistant",
        content=reply,
        confidence=confidence,
    ))

    # Auto-title the session from the first user message
    if not session.title:
        session.title = req.message[:100]

    await db.commit()

    return ChatResponse(
        reply=reply,
        session_id=session.id,
        sources=["Financial data from your workspace"],
        suggested_actions=[
            "View expense breakdown",
            "Check budget status",
            "Run a forecast",
        ],
        confidence=confidence,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream AI CFO response via Server-Sent Events (ADVANCE-002).

    SSE event format (JSON-framed for rich metadata):
        data: {"type":"meta","session_id":"...","sources":[...]}
        data: {"type":"token","content":"Hello"}
        data: {"type":"token","content":" world"}
        data: {"type":"done","session_id":"..."}

    Frontend usage:
        const res = await fetch('/api/chat/stream', {method: 'POST', ...});
        const reader = res.body.getReader();
    """
    session = await _get_or_create_session(db, user, req.session_id)
    context = await _build_context(db, user.workspace_id)

    # Get conversation history (last 10 messages)
    history_q = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.workspace_id == user.workspace_id,
                ChatMessage.session_id == session.id,
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history = list(reversed(list(history_q.scalars())))

    messages = [{"role": "system", "content": _build_system_prompt(context)}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    # Save user message immediately
    db.add(ChatMessage(
        workspace_id=user.workspace_id,
        user_id=user.id,
        session_id=session.id,
        role="user",
        content=req.message,
    ))
    if not session.title:
        session.title = req.message[:100]
    await db.commit()

    session_id_str = str(session.id)
    ws_id = user.workspace_id
    uid = user.id

    async def event_generator():
        """Yield JSON-framed SSE events as OpenAI returns tokens."""
        full_reply = []

        # ── Meta event: session info at stream start ──────────────
        meta = json.dumps({
            "type": "meta",
            "session_id": session_id_str,
            "sources": ["Financial data from your workspace"],
        })
        yield f"data: {meta}\n\n"

        try:
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            async with openai_traced(model=settings.OPENAI_MODEL, stream=True):
                stream = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_reply.append(delta.content)
                        token_evt = json.dumps({
                            "type": "token",
                            "content": delta.content,
                        })
                        yield f"data: {token_evt}\n\n"

        except Exception:
            fallback = (
                "I'm temporarily unable to connect to the AI service. "
                "Check your top expense categories for optimization opportunities."
            )
            full_reply.append(fallback)
            err_evt = json.dumps({"type": "token", "content": fallback})
            yield f"data: {err_evt}\n\n"

        # ── Done event ────────────────────────────────────────────
        done_evt = json.dumps({
            "type": "done",
            "session_id": session_id_str,
        })
        yield f"data: {done_evt}\n\n"

        # Save assistant reply to DB (after stream completes)
        from database import get_db_context
        async with get_db_context() as bg_db:
            bg_db.add(ChatMessage(
                workspace_id=ws_id,
                user_id=uid,
                session_id=uuid.UUID(session_id_str),
                role="assistant",
                content="".join(full_reply),
                confidence="high" if len(full_reply) > 1 else "low",
            ))
            await bg_db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "X-Session-Id": session_id_str,  # ADVANCE-002: session ID in header
        },
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the current user's workspace."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.workspace_id == user.workspace_id)
        .order_by(ChatSession.last_active_at.desc())
    )
    return list(result.scalars())


@router.get("/history")
async def chat_history(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a session (workspace-scoped)."""
    # Verify session ownership
    session_check = await db.execute(
        select(ChatSession.id).where(
            and_(
                ChatSession.id == session_id,
                ChatSession.workspace_id == user.workspace_id,
            )
        )
    )
    if not session_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found.")

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
