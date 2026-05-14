"""
AI CFO — Invoice Management Service
Sequential numbering, CRUD, payment tracking, aging reports.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Invoice, InvoicePayment, InvoiceSequence, InvoiceStatus

logger = logging.getLogger(__name__)


def _calculate_invoice_totals(items: list[dict], tax_rate: float) -> tuple[float, float, float]:
    subtotal = round(sum(float(item["amount"]) for item in items), 2)
    tax_amount = round(subtotal * float(tax_rate or 0), 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total


def _days_from_due_date(due_date: datetime | None, now: datetime | None = None) -> int:
    if due_date is None:
        return 0
    reference = now or datetime.now(timezone.utc)
    due = due_date if due_date.tzinfo else due_date.replace(tzinfo=timezone.utc)
    return (reference.date() - due.date()).days


async def _next_invoice_number(db: AsyncSession, ws_id: uuid.UUID) -> str:
    """Get next sequential invoice number using counter table with row lock."""
    result = await db.execute(
        select(InvoiceSequence).where(InvoiceSequence.workspace_id == ws_id).with_for_update()
    )
    seq = result.scalar_one_or_none()
    if seq:
        num = seq.next_number
        seq.next_number = num + 1
    else:
        num = 1
        db.add(InvoiceSequence(workspace_id=ws_id, next_number=2))
    await db.flush()
    return f"INV-{num:06d}"


async def list_invoices(db: AsyncSession, ws_id: uuid.UUID, status: str | None = None) -> list[Invoice]:
    q = select(Invoice).where(Invoice.workspace_id == ws_id)
    if status:
        q = q.where(Invoice.status == status)
    return list((await db.execute(q.order_by(Invoice.created_at.desc()))).scalars())


async def get_invoice(db: AsyncSession, ws_id: uuid.UUID, inv_id: uuid.UUID) -> Invoice | None:
    return (await db.execute(select(Invoice).where(
        and_(Invoice.id == inv_id, Invoice.workspace_id == ws_id)))).scalar_one_or_none()


async def create_invoice(db: AsyncSession, ws_id: uuid.UUID, user_id: uuid.UUID, data) -> Invoice:
    inv_number = await _next_invoice_number(db, ws_id)
    items = [item.model_dump() for item in data.items]
    subtotal, tax_amount, total = _calculate_invoice_totals(items, data.tax_rate)
    inv = Invoice(
        workspace_id=ws_id, user_id=user_id, invoice_number=inv_number,
        client_name=data.client_name, client_email=data.client_email,
        client_address=data.client_address, items_json=items,
        subtotal=Decimal(str(subtotal)), tax_rate=Decimal(str(data.tax_rate)),
        tax_amount=Decimal(str(tax_amount)), total=Decimal(str(total)),
        currency_code=data.currency_code,
        issue_date=datetime.strptime(data.issue_date, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        due_date=datetime.strptime(data.due_date, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        notes=data.notes, recurring_config_json=data.recurring_config,
    )
    db.add(inv); await db.flush(); await db.refresh(inv); return inv


async def update_invoice(db: AsyncSession, inv: Invoice, data) -> Invoice:
    if data.client_name is not None: inv.client_name = data.client_name
    if data.client_email is not None: inv.client_email = data.client_email
    if data.client_address is not None: inv.client_address = data.client_address
    if data.notes is not None: inv.notes = data.notes
    if data.status is not None: inv.status = data.status
    if data.items is not None:
        items = [i.model_dump() for i in data.items]
        inv.items_json = items
        tax_rate = float(data.tax_rate) if data.tax_rate is not None else float(inv.tax_rate)
        subtotal, tax_amount, total = _calculate_invoice_totals(items, tax_rate)
        inv.subtotal = Decimal(str(subtotal))
        inv.tax_rate = Decimal(str(tax_rate))
        inv.tax_amount = Decimal(str(tax_amount))
        inv.total = Decimal(str(total))
    if data.issue_date: inv.issue_date = datetime.strptime(data.issue_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if data.due_date: inv.due_date = datetime.strptime(data.due_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    await db.flush(); await db.refresh(inv); return inv


async def delete_invoice(db: AsyncSession, inv: Invoice) -> None:
    await db.delete(inv); await db.flush()


async def record_payment(db: AsyncSession, inv: Invoice, data) -> InvoicePayment:
    payment = InvoicePayment(
        invoice_id=inv.id, workspace_id=inv.workspace_id,
        amount=Decimal(str(data.amount)),
        payment_date=datetime.strptime(data.payment_date, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        payment_method=data.payment_method, reference=data.reference, notes=data.notes,
    )
    db.add(payment); await db.flush()
    inv.amount_paid = Decimal(str(float(inv.amount_paid) + data.amount))
    if float(inv.amount_paid) >= float(inv.total):
        inv.status = InvoiceStatus.paid
        inv.paid_date = datetime.now(timezone.utc)
    elif float(inv.amount_paid) > 0:
        inv.status = InvoiceStatus.partially_paid
    await db.flush(); await db.refresh(payment); return payment


async def get_aging_report(db: AsyncSession, ws_id: uuid.UUID):
    """Generate aging report with buckets: current, 1-30, 31-60, 61-90, 90+."""
    from schemas import AgingBucket, AgingReport, InvoiceOut
    now = datetime.now(timezone.utc)
    invoices = await list_invoices(db, ws_id)
    unpaid = [i for i in invoices if i.status not in (InvoiceStatus.paid, InvoiceStatus.cancelled, InvoiceStatus.draft)]
    buckets_def = [
        ("current", lambda d: d <= 0),
        ("1-30", lambda d: 1 <= d <= 30),
        ("31-60", lambda d: 31 <= d <= 60),
        ("61-90", lambda d: 61 <= d <= 90),
        ("90+", lambda d: d > 90),
    ]
    buckets = []
    total_outstanding = 0.0
    for label, check in buckets_def:
        matched = []
        for inv in unpaid:
            days_past_due = _days_from_due_date(inv.due_date, now)
            if check(days_past_due):
                matched.append(inv)
        bucket_total = sum(float(i.total) - float(i.amount_paid) for i in matched)
        total_outstanding += bucket_total
        buckets.append(AgingBucket(
            period=label, count=len(matched), total=round(bucket_total, 2),
            invoices=[InvoiceOut.model_validate(i) for i in matched[:5]],
        ))
    return AgingReport(total_outstanding=round(total_outstanding, 2), buckets=buckets)


async def send_invoice(db: AsyncSession, inv: Invoice) -> Invoice:
    """Mark invoice as sent."""
    inv.status = InvoiceStatus.sent
    await db.flush(); await db.refresh(inv); return inv
