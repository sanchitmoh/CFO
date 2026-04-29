"""
AI CFO — Chat Router
AI assistant with intent-gated RAG context and hardened prompts.
Sessions are UUID-identified, workspace-scoped, and user-owned.
Includes both blocking and streaming (SSE) endpoints.

RAG Pipeline (replaces legacy _build_context):
  1. Intent detection → route to relevant context fetchers only
  2. Semantic search via pgvector embeddings
  3. Confidence scoring injected into system prompt
  4. Sliding window history compression
  5. Hallucination guards + citation requirements
"""
import json
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import openai

from dependencies import get_rls_db
from auth import get_current_user
from models import User, ChatMessage, ChatSession
from schemas import ChatRequest, ChatResponse, ChatSessionOut
from config import settings
from telemetry import openai_traced
from services.chat_service import (
    build_context,
    compute_confidence,
    compress_history,
    build_system_prompt,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────


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


async def _prepare_messages(
    db: AsyncSession,
    user: User,
    session: ChatSession,
    user_message: str,
) -> tuple[list[dict], str, dict]:
    """Build the OpenAI messages array with intent-gated context and compressed history.

    Returns:
        (messages, confidence_level, metadata) — ready for OpenAI API call.
    """
    ws_id = user.workspace_id

    # ── 1. Intent-gated context retrieval ─────────────────────────
    context, metadata = await build_context(db, ws_id, user_message)
    confidence_level, confidence_note = compute_confidence(metadata)

    # ── 2. Hardened system prompt ─────────────────────────────────
    system_prompt = build_system_prompt(
        context=context,
        confidence_level=confidence_level,
        confidence_note=confidence_note,
        metadata=metadata,
    )

    # ── 3. Fetch & compress history ───────────────────────────────
    history_q = await db.execute(
        select(ChatMessage)
        .where(
            and_(
                ChatMessage.workspace_id == ws_id,
                ChatMessage.session_id == session.id,
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(20)  # fetch more than we need, compression will trim
    )
    history = list(reversed(list(history_q.scalars())))

    history_dicts = [
        {"role": msg.role, "content": msg.content} for msg in history
    ]
    compressed = compress_history(history_dicts)

    # ── 4. Assemble messages ──────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(compressed)
    messages.append({"role": "user", "content": user_message})

    logger.info(
        "Chat context built: intents=%s confidence=%s rag_matches=%d history_msgs=%d→%d",
        metadata.get("intents", []),
        confidence_level,
        metadata.get("rag_matches", 0),
        len(history_dicts),
        len(compressed),
    )

    return messages, confidence_level, metadata


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Send a message to the AI CFO assistant.

    Uses intent-gated RAG context, confidence-scored prompts,
    and sliding window history compression.
    """
    session = await _get_or_create_session(db, user, req.session_id)
    messages, confidence, metadata = await _prepare_messages(
        db, user, session, req.message,
    )

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

    # Build dynamic sources from metadata
    intents = metadata.get("intents", [])
    sources = ["Financial data from your workspace"]
    if metadata.get("rag_matches", 0) > 0:
        sources.append(f"{metadata['rag_matches']} semantically matched transactions")

    return ChatResponse(
        reply=reply,
        session_id=session.id,
        sources=sources,
        suggested_actions=_suggest_actions(intents),
        confidence=confidence,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Stream AI CFO response via Server-Sent Events (ADVANCE-002).

    SSE event format (JSON-framed for rich metadata):
        data: {"type":"meta","session_id":"...","confidence":"high","intents":[...]}
        data: {"type":"token","content":"Hello"}
        data: {"type":"token","content":" world"}
        data: {"type":"done","session_id":"..."}

    Frontend usage:
        const res = await fetch('/api/chat/stream', {method: 'POST', ...});
        const reader = res.body.getReader();
    """
    session = await _get_or_create_session(db, user, req.session_id)
    messages, confidence, metadata = await _prepare_messages(
        db, user, session, req.message,
    )

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

        # ── Meta event: session info + confidence at stream start ─
        sources = ["Financial data from your workspace"]
        if metadata.get("rag_matches", 0) > 0:
            sources.append(f"{metadata['rag_matches']} semantically matched transactions")

        meta = json.dumps({
            "type": "meta",
            "session_id": session_id_str,
            "confidence": confidence,
            "intents": metadata.get("intents", []),
            "sources": sources,
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
                confidence=confidence,
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


def _suggest_actions(intents: list[str]) -> list[str]:
    """Generate contextual suggested actions based on detected intents."""
    suggestions = {
        "balance": ["View expense breakdown", "Run a forecast"],
        "category_spend": ["Set category budgets", "Compare to last month"],
        "budgets": ["Adjust budget limits", "View overspend alerts"],
        "burn_rate": ["View cash runway", "Identify cost-cutting areas"],
        "flagged_transactions": ["Review all flagged items", "Set up alerts"],
        "search": ["Narrow search by category", "Export results"],
    }
    actions = []
    for intent in intents:
        actions.extend(suggestions.get(intent, []))
    if not actions:
        actions = [
            "View expense breakdown",
            "Check budget status",
            "Run a forecast",
        ]
    # Deduplicate while preserving order
    seen = set()
    return [a for a in actions if not (a in seen or seen.add(a))][:4]


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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
    db: AsyncSession = Depends(get_rls_db),
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
