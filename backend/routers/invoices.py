"""
AI CFO — Invoice Management Router
CRUD, payments, aging report, send.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User
from schemas import (
    InvoiceCreate, InvoiceUpdate, InvoiceOut,
    InvoicePaymentCreate, InvoicePaymentOut, AgingReport,
)
from services import invoice_service
from services.audit_service import log_action
from cache import invalidate_workspace_cache

router = APIRouter()


@router.get("/", response_model=list[InvoiceOut])
async def list_invoices(
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    invoices = await invoice_service.list_invoices(db, user.workspace_id, status_filter)
    return [InvoiceOut.model_validate(i) for i in invoices]


@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.create_invoice(db, user.workspace_id, user.id, data)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "invoice.create", "invoice", inv.id,
                     new_value={"number": inv.invoice_number, "client": data.client_name})
    return InvoiceOut.model_validate(inv)


@router.get("/aging", response_model=AgingReport)
async def aging_report(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await invoice_service.get_aging_report(db, user.workspace_id)


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.get_invoice(db, user.workspace_id, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut.model_validate(inv)


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.get_invoice(db, user.workspace_id, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = await invoice_service.update_invoice(db, inv, data)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    return InvoiceOut.model_validate(inv)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.get_invoice(db, user.workspace_id, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await log_action(db, user, "invoice.delete", "invoice", inv.id)
    await invoice_service.delete_invoice(db, inv)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
async def send_invoice(
    invoice_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.get_invoice(db, user.workspace_id, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = await invoice_service.send_invoice(db, inv)
    await db.commit()
    return InvoiceOut.model_validate(inv)


@router.post("/{invoice_id}/payments", response_model=InvoicePaymentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: uuid.UUID,
    data: InvoicePaymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    inv = await invoice_service.get_invoice(db, user.workspace_id, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    payment = await invoice_service.record_payment(db, inv, data)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    return InvoicePaymentOut.model_validate(payment)
