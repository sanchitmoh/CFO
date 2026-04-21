"""
AI CFO — Plaid Integration Service (ADVANCE-003)
Handles webhook signature verification, transaction sync via /transactions/sync,
and Plaid API client initialization.
"""
import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from crypto import encrypt_value, decrypt_value
from models import PlaidItem, Transaction, TransactionType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Plaid client initialization
# ═══════════════════════════════════════════════════════════════════

def _get_plaid_client():
    """Create a Plaid API client configured from settings."""
    try:
        import plaid
        from plaid.api import plaid_api
        from plaid.configuration import Configuration

        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production,
        }
        configuration = Configuration(
            host=env_map.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
            api_key={
                "clientId": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
            },
        )
        api_client = plaid.ApiClient(configuration)
        return plaid_api.PlaidApi(api_client)
    except ImportError:
        logger.error("plaid-python not installed. Run: pip install plaid-python")
        raise


# ═══════════════════════════════════════════════════════════════════
# Webhook signature verification
# ═══════════════════════════════════════════════════════════════════

async def verify_webhook_signature(body: bytes, headers: dict) -> bool:
    """Verify Plaid webhook using the Plaid-Verification header.

    Plaid uses a signed JWT for webhook verification. In sandbox mode,
    we accept all webhooks for easier testing.
    """
    if settings.PLAID_ENV == "sandbox":
        return True  # Skip verification in sandbox

    verification_header = headers.get("plaid-verification")
    if not verification_header:
        logger.warning("Plaid webhook missing verification header")
        return False

    try:
        # In production, verify the JWT using Plaid's JWKS endpoint
        # For now, we do a basic check that the header is present
        # Full verification requires: plaid_client.webhook_verification_key_get()
        # and JWT validation against Plaid's public keys
        client = _get_plaid_client()
        from plaid.model.webhook_verification_key_get_request import (
            WebhookVerificationKeyGetRequest,
        )
        import jose.jwt as jwt

        # Decode JWT header to get key_id
        decoded_header = jwt.get_unverified_header(verification_header)
        key_id = decoded_header.get("kid")

        if not key_id:
            return False

        # Fetch the verification key from Plaid
        key_request = WebhookVerificationKeyGetRequest(key_id=key_id)
        key_response = client.webhook_verification_key_get(key_request)
        key = key_response.key

        # Verify JWT
        claims = jwt.decode(
            verification_header,
            key,
            algorithms=["ES256"],
        )

        # Verify body hash
        body_hash = hashlib.sha256(body).hexdigest()
        if claims.get("request_body_sha256") != body_hash:
            return False

        # Verify timestamp (within 5 minutes)
        iat = claims.get("iat", 0)
        if abs(time.time() - iat) > 300:
            return False

        return True

    except Exception as exc:
        logger.error("Plaid webhook verification failed: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════
# Link token creation
# ═══════════════════════════════════════════════════════════════════

async def create_link_token(user_id: str) -> dict:
    """Create a Plaid Link token for the frontend Link flow."""
    client = _get_plaid_client()

    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
        client_name="AI CFO",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
        webhook=settings.PLAID_WEBHOOK_URL or None,
    )

    response = client.link_token_create(request)
    return {
        "link_token": response.link_token,
        "expiration": response.expiration,
    }


# ═══════════════════════════════════════════════════════════════════
# Public token exchange
# ═══════════════════════════════════════════════════════════════════

async def exchange_public_token(
    db: AsyncSession,
    public_token: str,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    institution_id: Optional[str] = None,
    institution_name: Optional[str] = None,
) -> PlaidItem:
    """Exchange a Plaid public token for an access token and store it."""
    client = _get_plaid_client()

    from plaid.model.item_public_token_exchange_request import (
        ItemPublicTokenExchangeRequest,
    )

    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)

    access_token = response.access_token
    item_id = response.item_id

    # Encrypt the access token before storage
    encrypted_token = encrypt_value(access_token)

    plaid_item = PlaidItem(
        workspace_id=workspace_id,
        user_id=user_id,
        item_id=item_id,
        access_token_encrypted=encrypted_token,
        institution_id=institution_id,
        institution_name=institution_name,
    )
    db.add(plaid_item)
    await db.commit()
    await db.refresh(plaid_item)

    logger.info(
        "Plaid item created: %s (%s) for workspace %s",
        item_id, institution_name, workspace_id,
    )
    return plaid_item


# ═══════════════════════════════════════════════════════════════════
# Transaction sync (incremental via cursor)
# ═══════════════════════════════════════════════════════════════════

async def sync_transactions(
    db: AsyncSession,
    plaid_item: PlaidItem,
) -> dict:
    """Sync transactions from Plaid using the /transactions/sync endpoint.

    Uses a cursor for incremental updates — only fetches new/modified/removed
    transactions since the last sync.

    Returns: {"added": N, "modified": N, "removed": N}
    """
    client = _get_plaid_client()
    access_token = decrypt_value(plaid_item.access_token_encrypted)

    from plaid.model.transactions_sync_request import TransactionsSyncRequest

    added_count = 0
    modified_count = 0
    removed_count = 0
    has_more = True
    cursor = plaid_item.sync_cursor

    while has_more:
        request_kwargs = {"access_token": access_token}
        if cursor:
            request_kwargs["cursor"] = cursor

        request = TransactionsSyncRequest(**request_kwargs)
        response = client.transactions_sync(request)

        # ── Process added transactions ────────────────────────────
        for txn in response.added:
            db_txn = _map_plaid_transaction(txn, plaid_item.workspace_id, plaid_item.user_id)
            db.add(db_txn)
            added_count += 1

        # ── Process modified transactions ─────────────────────────
        for txn in response.modified:
            # Find existing transaction by plaid transaction_id
            existing = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.workspace_id == plaid_item.workspace_id,
                        Transaction.notes == f"plaid:{txn.transaction_id}",
                    )
                )
            )
            existing_txn = existing.scalar_one_or_none()
            if existing_txn:
                existing_txn.amount = abs(txn.amount)
                existing_txn.description = txn.name or txn.merchant_name or "Unknown"
                existing_txn.category = (txn.personal_finance_category or {}).get(
                    "primary", "Uncategorized"
                ) if hasattr(txn, "personal_finance_category") else "Uncategorized"
                modified_count += 1

        # ── Process removed transactions ──────────────────────────
        for removed in response.removed:
            existing = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.workspace_id == plaid_item.workspace_id,
                        Transaction.notes == f"plaid:{removed.transaction_id}",
                    )
                )
            )
            existing_txn = existing.scalar_one_or_none()
            if existing_txn:
                await db.delete(existing_txn)
                removed_count += 1

        cursor = response.next_cursor
        has_more = response.has_more

    # Update sync cursor and timestamp
    plaid_item.sync_cursor = cursor
    plaid_item.last_synced_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "Plaid sync complete for item %s: +%d ~%d -%d",
        plaid_item.item_id, added_count, modified_count, removed_count,
    )
    return {
        "added": added_count,
        "modified": modified_count,
        "removed": removed_count,
    }


def _map_plaid_transaction(plaid_txn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Transaction:
    """Convert a Plaid transaction to our Transaction model."""
    amount = abs(plaid_txn.amount)  # Plaid uses negative for debits

    # Determine type: Plaid negative = income, positive = expense
    txn_type = TransactionType.income if plaid_txn.amount < 0 else TransactionType.expense

    # Extract category from personal_finance_category
    category = "Uncategorized"
    if hasattr(plaid_txn, "personal_finance_category") and plaid_txn.personal_finance_category:
        pfc = plaid_txn.personal_finance_category
        category = getattr(pfc, "primary", None) or "Uncategorized"

    return Transaction(
        workspace_id=workspace_id,
        user_id=user_id,
        date=datetime.combine(plaid_txn.date, datetime.min.time()),
        description=plaid_txn.name or plaid_txn.merchant_name or "Unknown",
        amount=amount,
        category=category,
        type=txn_type,
        account=plaid_txn.account_id[:20] if plaid_txn.account_id else "Plaid",
        vendor=plaid_txn.merchant_name,
        notes=f"plaid:{plaid_txn.transaction_id}",  # Link back to Plaid
        source="api",
    )
