"""
AI CFO — Vendor Management Router
CRUD, spend analytics, fuzzy duplicate detection,
performance scoring, contract management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User
from schemas import (
    VendorCreate, VendorUpdate, VendorOut, VendorContactCreate, VendorContactOut,
    VendorSpendAnalysis, DuplicateVendorResult,
    VendorReviewCreate, VendorReviewOut, VendorScorecard,
    ContractCreate, ContractUpdate, ContractOut, ContractExpiringSoon,
)
from services import vendor_service
from services.audit_service import log_action
from cache import invalidate_workspace_cache

router = APIRouter()


@router.get("/", response_model=list[VendorOut])
async def list_vendors(
    active_only: bool = Query(True),
    category: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendors = await vendor_service.list_vendors(db, user.workspace_id, active_only, category)
    spend_map = await vendor_service.get_vendor_spend_map(db, user.workspace_id)
    result = []
    for v in vendors:
        out = VendorOut.model_validate(v)
        stats = spend_map.get(v.name.lower(), {})
        out.total_spent = stats.get("total_spent", 0.0)
        out.transaction_count = stats.get("transaction_count", 0)
        result.append(out)
    return result


@router.post("/sync-from-transactions", status_code=status.HTTP_200_OK)
async def sync_vendors_from_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Back-fill the vendors table from unique transaction vendor names.

    Use this after importing CSV data to auto-create vendor records
    for all distinct vendor names found in the transactions table.
    """
    created = await vendor_service.sync_vendors_from_transactions(db, user.workspace_id)
    await db.commit()
    if created:
        await invalidate_workspace_cache(str(user.workspace_id))
    return {"created": created, "message": f"Synced {created} new vendor(s) from transactions."}


@router.post("/", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    data: VendorCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.create_vendor(db, user.workspace_id, data)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "vendor.create", "vendor", vendor.id, new_value={"name": data.name})
    return VendorOut.model_validate(vendor)


@router.get("/spend-analysis", response_model=list[VendorSpendAnalysis])
async def spend_analysis(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await vendor_service.vendor_spend_analysis(db, user.workspace_id)


@router.get("/monthly-trend")
async def monthly_trend(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await vendor_service.vendor_monthly_trend(db, user.workspace_id)


@router.get("/vendor-transactions")
async def vendor_transactions(
    name: str = Query(..., description="Vendor name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await vendor_service.vendor_transactions(db, user.workspace_id, name, skip=skip, limit=limit)


@router.get("/duplicates", response_model=list[DuplicateVendorResult])
async def find_duplicates(
    threshold: float = Query(0.75, ge=0.5, le=1.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await vendor_service.find_duplicates(db, user.workspace_id, threshold)


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return VendorOut.model_validate(vendor)


@router.put("/{vendor_id}", response_model=VendorOut)
async def update_vendor(
    vendor_id: uuid.UUID,
    data: VendorUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor = await vendor_service.update_vendor(db, vendor, data)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    return VendorOut.model_validate(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await log_action(db, user, "vendor.delete", "vendor", vendor.id)
    await vendor_service.delete_vendor(db, vendor)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))


@router.post("/{vendor_id}/contacts", response_model=VendorContactOut, status_code=status.HTTP_201_CREATED)
async def add_contact(
    vendor_id: uuid.UUID,
    data: VendorContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    contact = await vendor_service.add_contact(db, vendor, data)
    await db.commit()
    return VendorContactOut.model_validate(contact)


# ═══════════════════════════════════════════════════════════════════
# VENDOR PERFORMANCE REVIEWS & SCORECARDS
# ═══════════════════════════════════════════════════════════════════

@router.post("/{vendor_id}/reviews", response_model=VendorReviewOut, status_code=status.HTTP_201_CREATED)
async def submit_review(
    vendor_id: uuid.UUID,
    data: VendorReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    review = await vendor_service.submit_review(db, user.workspace_id, vendor_id, user.id, data)
    await db.commit()
    await log_action(db, user, "vendor.review", "vendor", vendor_id,
                     new_value={"composite": f"{data.delivery_rating+data.quality_rating+data.responsiveness_rating+data.cost_rating}/20"})
    return VendorReviewOut.model_validate(review)


@router.get("/{vendor_id}/reviews", response_model=list[VendorReviewOut])
async def list_reviews(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    reviews = await vendor_service.list_reviews(db, user.workspace_id, vendor_id)
    return [VendorReviewOut.model_validate(r) for r in reviews]


@router.get("/{vendor_id}/scorecard", response_model=VendorScorecard)
async def get_scorecard(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scorecard = await vendor_service.get_vendor_scorecard(db, user.workspace_id, vendor_id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return scorecard


# ═══════════════════════════════════════════════════════════════════
# VENDOR CONTRACT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.get("/contracts/expiring", response_model=list[ContractExpiringSoon])
async def expiring_contracts(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await vendor_service.get_expiring_contracts(db, user.workspace_id, days)


@router.post("/{vendor_id}/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    vendor_id: uuid.UUID,
    data: ContractCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    vendor = await vendor_service.get_vendor(db, user.workspace_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    contract = await vendor_service.create_contract(db, user.workspace_id, vendor_id, data)
    await db.commit()
    await log_action(db, user, "contract.create", "contract", contract.id,
                     new_value={"title": data.title, "vendor": vendor.name})
    return ContractOut.model_validate(contract)


@router.get("/{vendor_id}/contracts", response_model=list[ContractOut])
async def list_contracts(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    contracts = await vendor_service.list_contracts(db, user.workspace_id, vendor_id)
    return [ContractOut.model_validate(c) for c in contracts]


@router.put("/contracts/{contract_id}", response_model=ContractOut)
async def update_contract(
    contract_id: uuid.UUID,
    data: ContractUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    contract = await vendor_service.get_contract(db, user.workspace_id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract = await vendor_service.update_contract(db, contract, data)
    await db.commit()
    return ContractOut.model_validate(contract)
