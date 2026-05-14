from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from models import Invoice, InvoiceStatus
from schemas import AgingBucket, InvoiceCreate, InvoiceOut
from services.invoice_service import _calculate_invoice_totals


def test_invoice_create_accepts_frontend_payload_and_normalizes_tax_rate():
    payload = {
        "client_name": "Acme Corp",
        "client_email": "billing@acme.example.com",
        "issue_date": "2026-05-14",
        "due_date": "2026-05-29",
        "line_items": [
            {"description": "Consulting", "quantity": 2, "unit_price": 1250},
            {"description": "Hosting", "quantity": 1, "unit_price": 499.99},
        ],
        "tax_rate": 0.18,
        "notes": "Net 15",
    }

    invoice = InvoiceCreate.model_validate(payload)

    assert [item.amount for item in invoice.items] == [2500.0, 499.99]
    assert invoice.tax_rate == 0.18


def test_invoice_create_accepts_whole_percent_tax_rate():
    payload = {
        "client_name": "Acme Corp",
        "issue_date": "2026-05-14",
        "due_date": "2026-05-29",
        "items": [
            {"description": "Consulting", "quantity": 2, "unit_price": 1250},
        ],
        "tax_rate": 18,
    }

    invoice = InvoiceCreate.model_validate(payload)

    assert invoice.tax_rate == 0.18


def test_invoice_out_exposes_frontend_friendly_fields():
    now = datetime.now(timezone.utc)
    invoice = Invoice(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        invoice_number="INV-000123",
        client_name="Acme Corp",
        client_email="billing@acme.example.com",
        client_address="Mumbai",
        items_json=[
            {"description": "Consulting", "quantity": 2, "unit_price": 1250, "amount": 2500},
            {"description": "Hosting", "quantity": 1, "unit_price": 499.99},
        ],
        subtotal=Decimal("2999.99"),
        tax_rate=Decimal("0.1800"),
        tax_amount=Decimal("540.00"),
        total=Decimal("3539.99"),
        amount_paid=Decimal("500.00"),
        currency_code="INR",
        status=InvoiceStatus.sent,
        issue_date=now - timedelta(days=10),
        due_date=now - timedelta(days=5, minutes=1),
        notes="Net 15",
        created_at=now - timedelta(days=10),
    )

    payload = InvoiceOut.model_validate(invoice).model_dump()

    assert payload["line_items"][0]["amount"] == 2500.0
    assert payload["line_items"][1]["amount"] == 499.99
    assert payload["amount_due"] == 3039.99
    assert payload["days_overdue"] >= 5
    assert payload["tax_rate"] == 0.18


def test_aging_bucket_accepts_period_and_serializes_bucket():
    bucket = AgingBucket.model_validate(
        {"period": "1-30", "count": 2, "total": 3039.99, "invoices": []}
    )
    payload = bucket.model_dump()

    assert payload["bucket"] == "1-30"
    assert payload["period"] == "1-30"


def test_invoice_total_calculation_uses_fractional_tax_rate():
    subtotal, tax_amount, total = _calculate_invoice_totals(
        [{"amount": 7200.0}],
        0.18,
    )

    assert subtotal == 7200.0
    assert tax_amount == 1296.0
    assert total == 8496.0
