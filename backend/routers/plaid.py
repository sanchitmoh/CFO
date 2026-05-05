"""
AI CFO — Plaid Router (ADVANCE-003)
Webhook receiver, Link token creation, and public token exchange.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_context
from dependencies import get_rls_db
from auth import get_current_user
from models import User, PlaidItem
from services.plaid_service import (
    verify_webhook_signature,
    create_link_token,
    exchange_public_token,
    sync_transactions,
)
from services.audit_service import log_action
from cache import invalidate_workspace_cache

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request schemas ────────────────────────────────────────────────

class LinkTokenRequest(BaseModel):
    """No body needed — user comes from auth."""
    pass


class ExchangeTokenRequest(BaseModel):
    public_token: str
    institution_id: str | None = None
    institution_name: str | None = None


# ── Webhook endpoint (no auth — signature verified) ───────────────


@router.post("/webhook")
async def plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive and process Plaid webhook events.

    This endpoint has NO authentication — Plaid sends webhooks directly.
    We verify authenticity via the Plaid-Verification signature header.

    Supported webhook_types:
      - TRANSACTIONS: SYNC_UPDATES_AVAILABLE, DEFAULT_UPDATE, INITIAL_UPDATE
    """
    body = await request.body()
    headers = dict(request.headers)

    # Verify webhook signature
    if not await verify_webhook_signature(body, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    webhook_type = payload.get("webhook_type", "")
    webhook_code = payload.get("webhook_code", "")
    item_id = payload.get("item_id", "")

    logger.info("Plaid webhook: %s / %s for item %s", webhook_type, webhook_code, item_id)

    if webhook_type == "TRANSACTIONS" and webhook_code in (
        "SYNC_UPDATES_AVAILABLE",
        "DEFAULT_UPDATE",
        "INITIAL_UPDATE",
    ):
        # Trigger sync in the background
        async def _sync_item():
            # Phase 1: Lookup PlaidItem with plain session (no user context)
            async with get_db_context() as db:
                result = await db.execute(
                    select(PlaidItem).where(
                        and_(PlaidItem.item_id == item_id, PlaidItem.is_active.is_(True))
                    )
                )
                plaid_item = result.scalar_one_or_none()
                if not plaid_item:
                    logger.warning("Plaid item not found: %s", item_id)
                    return
                ws_id = str(plaid_item.workspace_id)

            # Phase 2: Sync under RLS-bound session for tenant isolation
            from database import get_rls_db_context
            async with get_rls_db_context(ws_id) as rls_db:
                # Re-fetch the item within the RLS session
                result = await rls_db.execute(
                    select(PlaidItem).where(
                        and_(PlaidItem.item_id == item_id, PlaidItem.is_active.is_(True))
                    )
                )
                plaid_item = result.scalar_one_or_none()
                if plaid_item:
                    stats = await sync_transactions(rls_db, plaid_item)
                    logger.info(
                        "Background sync for %s: %s", item_id, stats
                    )
                    # Invalidate dashboard cache for this workspace
                    await invalidate_workspace_cache(ws_id)

        background_tasks.add_task(_sync_item)

    return {"status": "received", "webhook_type": webhook_type, "webhook_code": webhook_code}


# ── Link token (authenticated) ────────────────────────────────────


@router.post("/link-token")
async def get_link_token(
    user: User = Depends(get_current_user),
):
    """Create a Plaid Link token for the frontend to initiate the Link flow."""
    try:
        result = await create_link_token(str(user.id))
        return result
    except Exception as exc:
        logger.error("Failed to create link token: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create Plaid Link token")


# ── Exchange token (authenticated) ────────────────────────────────


@router.post("/exchange-token")
async def exchange_token(
    data: ExchangeTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Exchange a Plaid public token for an access token after Link flow.

    This stores the encrypted access token and immediately triggers
    the first transaction sync.
    """
    try:
        plaid_item = await exchange_public_token(
            db=db,
            public_token=data.public_token,
            workspace_id=user.workspace_id,
            user_id=user.id,
            institution_id=data.institution_id,
            institution_name=data.institution_name,
        )

        await log_action(
            db, user, "plaid.connect", "plaid_item", plaid_item.id,
            new_value={"institution": data.institution_name},
        )

        # Trigger initial sync
        stats = await sync_transactions(db, plaid_item)
        await invalidate_workspace_cache(str(user.workspace_id))

        return {
            "item_id": plaid_item.item_id,
            "institution": data.institution_name,
            "sync_result": stats,
        }

    except Exception as exc:
        logger.error("Failed to exchange token: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to connect bank account")


# ── List connected accounts ───────────────────────────────────────


@router.get("/accounts")
async def list_plaid_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List all connected Plaid accounts for the workspace."""
    result = await db.execute(
        select(PlaidItem)
        .where(
            and_(
                PlaidItem.workspace_id == user.workspace_id,
                PlaidItem.is_active.is_(True),
            )
        )
        .order_by(PlaidItem.created_at.desc())
    )
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "item_id": item.item_id,
            "institution_name": item.institution_name,
            "last_synced_at": item.last_synced_at.isoformat() if item.last_synced_at else None,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
