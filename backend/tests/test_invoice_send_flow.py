from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi import HTTPException

from models import Invoice, InvoiceStatus
from routers.invoices import send_invoice as send_invoice_route
from services.email_service import EmailService
from services.invoice_service import get_aging_report


def _make_invoice(
    *,
    invoice_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: InvoiceStatus = InvoiceStatus.draft,
    client_email: str | None = "billing@acme.example.com",
    due_date: datetime | None = None,
) -> Invoice:
    now = datetime.now(timezone.utc)
    return Invoice(
        id=invoice_id or uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        invoice_number="INV-000777",
        client_name="Acme Corp",
        client_email=client_email,
        client_address="Mumbai",
        items_json=[
            {"description": "Cloths", "quantity": 1.0, "unit_price": 50000.0, "amount": 50000.0},
        ],
        subtotal=Decimal("50000.00"),
        tax_rate=Decimal("0.1800"),
        tax_amount=Decimal("9000.00"),
        total=Decimal("59000.00"),
        amount_paid=Decimal("0.00"),
        currency_code="INR",
        status=status,
        issue_date=now - timedelta(days=1),
        due_date=due_date or now + timedelta(days=7),
        notes="Net 15",
        created_at=now - timedelta(days=1),
    )


@pytest.mark.anyio
async def test_send_invoice_email_uses_invoice_recipient_and_content():
    service = EmailService()
    invoice = _make_invoice()

    with patch.object(service, "send_email", new=AsyncMock(return_value=True)) as send_email_mock:
        success = await service.send_invoice_email(invoice)

    assert success is True
    kwargs = send_email_mock.await_args.kwargs
    assert kwargs["to_addresses"] == [invoice.client_email]
    assert invoice.invoice_number in kwargs["subject"]
    assert "Cloths" in kwargs["html_content"]


@pytest.mark.anyio
async def test_send_invoice_route_sends_email_before_marking_status():
    user = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
    draft_invoice = _make_invoice(workspace_id=user.workspace_id, user_id=user.id, status=InvoiceStatus.draft)
    sent_invoice = _make_invoice(
        invoice_id=draft_invoice.id,
        workspace_id=user.workspace_id,
        user_id=user.id,
        status=InvoiceStatus.sent,
    )
    db = SimpleNamespace(commit=AsyncMock())

    with patch("routers.invoices.invoice_service.get_invoice", new=AsyncMock(return_value=draft_invoice)), \
         patch("routers.invoices.email_service.send_invoice_email", new=AsyncMock(return_value=True)) as email_mock, \
         patch("routers.invoices.invoice_service.send_invoice", new=AsyncMock(return_value=sent_invoice)) as send_mock, \
         patch("routers.invoices.invalidate_workspace_cache", new=AsyncMock()) as invalidate_mock, \
         patch("routers.invoices.log_action", new=AsyncMock()) as log_mock:
        result = await send_invoice_route(draft_invoice.id, user, db)

    assert result.status == "sent"
    email_mock.assert_awaited_once_with(draft_invoice)
    send_mock.assert_awaited_once_with(db, draft_invoice)
    db.commit.assert_awaited_once()
    invalidate_mock.assert_awaited_once_with(str(user.workspace_id))
    log_mock.assert_awaited()


@pytest.mark.anyio
async def test_send_invoice_route_rejects_missing_client_email():
    user = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
    invoice = _make_invoice(workspace_id=user.workspace_id, user_id=user.id, client_email=None)
    db = SimpleNamespace(commit=AsyncMock())

    with patch("routers.invoices.invoice_service.get_invoice", new=AsyncMock(return_value=invoice)), \
         patch("routers.invoices.email_service.send_invoice_email", new=AsyncMock()) as email_mock, \
         patch("routers.invoices.invoice_service.send_invoice", new=AsyncMock()) as send_mock:
        with pytest.raises(HTTPException) as exc:
            await send_invoice_route(invoice.id, user, db)

    assert exc.value.status_code == 400
    email_mock.assert_not_called()
    send_mock.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.anyio
async def test_send_invoice_route_returns_502_when_delivery_fails():
    user = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4())
    invoice = _make_invoice(workspace_id=user.workspace_id, user_id=user.id)
    db = SimpleNamespace(commit=AsyncMock())

    with patch("routers.invoices.invoice_service.get_invoice", new=AsyncMock(return_value=invoice)), \
         patch("routers.invoices.email_service.send_invoice_email", new=AsyncMock(return_value=False)) as email_mock, \
         patch("routers.invoices.invoice_service.send_invoice", new=AsyncMock()) as send_mock:
        with pytest.raises(HTTPException) as exc:
            await send_invoice_route(invoice.id, user, db)

    assert exc.value.status_code == 502
    email_mock.assert_awaited_once_with(invoice)
    send_mock.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.anyio
async def test_aging_report_treats_invoice_due_today_as_current():
    now = datetime.now(timezone.utc)
    invoice = _make_invoice(
        status=InvoiceStatus.sent,
        due_date=now.replace(hour=0, minute=0, second=0, microsecond=0),
    )

    with patch("services.invoice_service.list_invoices", new=AsyncMock(return_value=[invoice])):
        report = await get_aging_report(AsyncMock(), invoice.workspace_id)

    current_bucket = next(bucket for bucket in report.buckets if bucket.bucket == "current")
    first_overdue_bucket = next(bucket for bucket in report.buckets if bucket.bucket == "1-30")

    assert current_bucket.count == 1
    assert first_overdue_bucket.count == 0
    assert current_bucket.invoices[0].days_overdue == 0
