"""
AI CFO — Vendor Management Service
CRUD + fuzzy matching + spend analytics + performance scoring + contract management.
"""
import uuid
import logging
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import (
    Vendor, VendorContact, VendorReview, VendorContract,
    Transaction, TransactionType, ContractStatus,
)
from schemas import (
    VendorCreate, VendorUpdate, VendorOut, VendorContactCreate,
    VendorSpendAnalysis, DuplicateVendorResult,
    VendorReviewCreate, VendorReviewOut, VendorScorecard,
    ContractCreate, ContractUpdate, ContractOut, ContractExpiringSoon,
)

logger = logging.getLogger(__name__)


# ── Fuzzy Matching ─────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Normalize vendor name for matching: lowercase, strip common suffixes."""
    import re
    name = name.lower().strip()
    # Remove common legal suffixes
    for suffix in [
        r"\bpvt\.?\s*ltd\.?\b", r"\bprivate\s+limited\b",
        r"\bllc\b", r"\binc\.?\b", r"\bcorp\.?\b",
        r"\bltd\.?\b", r"\blimited\b", r"\b& co\.?\b",
    ]:
        name = re.sub(suffix, "", name)
    # Remove extra whitespace and punctuation
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _similarity(a: str, b: str) -> float:
    """Compute similarity between two vendor names (0.0 to 1.0)."""
    norm_a = _normalize(a)
    norm_b = _normalize(b)
    if norm_a == norm_b:
        return 1.0
    # SequenceMatcher for general similarity
    seq_ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    # Check if one contains the other
    containment_bonus = 0.0
    if norm_a in norm_b or norm_b in norm_a:
        containment_bonus = 0.15
    return min(seq_ratio + containment_bonus, 1.0)


async def find_duplicates(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    threshold: float = 0.75,
) -> list[DuplicateVendorResult]:
    """Find potential duplicate vendors using fuzzy matching."""
    result = await db.execute(
        select(Vendor).where(
            and_(Vendor.workspace_id == workspace_id, Vendor.is_active.is_(True))
        )
    )
    vendors = list(result.scalars())
    duplicates = []
    for i in range(len(vendors)):
        for j in range(i + 1, len(vendors)):
            score = _similarity(vendors[i].name, vendors[j].name)
            if score >= threshold:
                duplicates.append(DuplicateVendorResult(
                    vendor_a=vendors[i].name,
                    vendor_b=vendors[j].name,
                    similarity_score=round(score, 3),
                ))
    duplicates.sort(key=lambda d: d.similarity_score, reverse=True)
    return duplicates


# ── CRUD ───────────────────────────────────────────────────────────

async def list_vendors(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    active_only: bool = True,
    category: str | None = None,
) -> list[Vendor]:
    query = select(Vendor).options(selectinload(Vendor.contacts)).where(
        Vendor.workspace_id == workspace_id
    )
    if active_only:
        query = query.where(Vendor.is_active.is_(True))
    if category:
        query = query.where(Vendor.category == category)
    query = query.order_by(Vendor.name)
    result = await db.execute(query)
    return list(result.scalars())


async def get_vendor_spend_map(
    db: AsyncSession, workspace_id: uuid.UUID,
) -> dict[str, dict]:
    """Return {lowercase_vendor_name: {total_spent, transaction_count}} from transactions."""
    result = await db.execute(
        select(
            func.lower(Transaction.vendor).label("vendor_lower"),
            func.sum(Transaction.amount).label("total_spent"),
            func.count(Transaction.id).label("txn_count"),
        ).where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.vendor.isnot(None),
                Transaction.vendor != "",
                Transaction.type == TransactionType.expense,
            )
        ).group_by(func.lower(Transaction.vendor))
    )
    return {
        row.vendor_lower: {
            "total_spent": float(row.total_spent or 0),
            "transaction_count": int(row.txn_count or 0),
        }
        for row in result.all()
    }


async def get_vendor(
    db: AsyncSession, workspace_id: uuid.UUID, vendor_id: uuid.UUID
) -> Vendor | None:
    result = await db.execute(
        select(Vendor)
        .options(selectinload(Vendor.contacts))
        .where(and_(Vendor.id == vendor_id, Vendor.workspace_id == workspace_id))
    )
    return result.scalar_one_or_none()


async def create_vendor(
    db: AsyncSession, workspace_id: uuid.UUID, data: VendorCreate
) -> Vendor:
    vendor = Vendor(
        workspace_id=workspace_id,
        name=data.name,
        display_name=data.display_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        payment_terms_days=data.payment_terms_days,
        category=data.category,
        tax_id=data.tax_id,
        notes=data.notes,
    )
    db.add(vendor)
    await db.flush()
    await db.refresh(vendor)
    return vendor


async def sync_vendors_from_transactions(
    db: AsyncSession, workspace_id: uuid.UUID,
) -> int:
    """Auto-create Vendor records from unique transaction.vendor values.

    Scans the transactions table for distinct, non-null vendor names that
    don't yet have a matching row in the vendors table (case-insensitive)
    and inserts them with the most common category.
    Returns the number of new vendors created.
    """
    # 1. Get vendor names with their most common category
    txn_result = await db.execute(
        select(
            Transaction.vendor,
            Transaction.category,
            func.count(Transaction.id).label("cnt"),
        ).where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.vendor.isnot(None),
                Transaction.vendor != "",
            )
        ).group_by(Transaction.vendor, Transaction.category)
        .order_by(Transaction.vendor, func.count(Transaction.id).desc())
    )

    # Build {vendor_name: best_category} — first row per vendor wins (highest count)
    vendor_categories: dict[str, str] = {}
    for row in txn_result.all():
        name = row[0].strip() if row[0] else ""
        cat = row[1] or "Uncategorized"
        if name and name not in vendor_categories:
            vendor_categories[name] = cat

    if not vendor_categories:
        return 0

    # 2. Get existing vendor names (lower-cased for comparison)
    existing_result = await db.execute(
        select(func.lower(Vendor.name)).where(Vendor.workspace_id == workspace_id)
    )
    existing_names: set[str] = {row[0] for row in existing_result.all()}

    # 3. Insert vendors that don't already exist
    created = 0
    for name, category in vendor_categories.items():
        if name.lower() not in existing_names:
            vendor = Vendor(
                workspace_id=workspace_id,
                name=name,
                display_name=name,
                category=category,
                is_active=True,
            )
            db.add(vendor)
            existing_names.add(name.lower())
            created += 1

    # 4. Update existing vendors that still have "Uncategorized"
    uncategorized_result = await db.execute(
        select(Vendor).where(
            and_(
                Vendor.workspace_id == workspace_id,
                Vendor.category == "Uncategorized",
            )
        )
    )
    for v in uncategorized_result.scalars():
        best_cat = vendor_categories.get(v.name)
        if best_cat and best_cat != "Uncategorized":
            v.category = best_cat

    if created:
        await db.flush()
        logger.info("sync_vendors: created %d vendors for workspace %s", created, workspace_id)

    return created


async def update_vendor(
    db: AsyncSession, vendor: Vendor, data: VendorUpdate
) -> Vendor:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    await db.flush()
    await db.refresh(vendor)
    return vendor


async def delete_vendor(db: AsyncSession, vendor: Vendor) -> None:
    await db.delete(vendor)
    await db.flush()


async def add_contact(
    db: AsyncSession, vendor: Vendor, data: VendorContactCreate
) -> VendorContact:
    contact = VendorContact(
        vendor_id=vendor.id,
        workspace_id=vendor.workspace_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        role=data.role,
        is_primary=data.is_primary,
    )
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return contact


# ── Spend Analytics ────────────────────────────────────────────────

async def vendor_spend_analysis(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[VendorSpendAnalysis]:
    """Aggregate spending by vendor name."""
    result = await db.execute(
        select(
            Transaction.vendor,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
            func.avg(Transaction.amount),
            func.max(Transaction.date),
            Transaction.category,
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.vendor.isnot(None),
                Transaction.vendor != "",
            )
        )
        .group_by(Transaction.vendor, Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(30)
    )
    rows = result.fetchall()
    return [
        VendorSpendAnalysis(
            vendor_name=row[0] or "Unknown",
            total_spend=float(row[1] or 0),
            transaction_count=int(row[2] or 0),
            avg_transaction=round(float(row[3] or 0), 2),
            last_transaction_date=row[4].isoformat() if row[4] else None,
            category=row[5] or "Uncategorized",
        )
        for row in rows
    ]


async def vendor_monthly_trend(
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[dict]:
    """Return monthly spending aggregated across top vendors."""
    result = await db.execute(
        select(
            func.date_trunc("month", Transaction.date).label("month"),
            Transaction.vendor,
            func.sum(Transaction.amount).label("total"),
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.vendor.isnot(None),
                Transaction.vendor != "",
            )
        )
        .group_by("month", Transaction.vendor)
        .order_by("month")
    )
    return [
        {
            "month": row.month.strftime("%Y-%m") if row.month else "",
            "vendor": row.vendor,
            "total": float(row.total or 0),
        }
        for row in result.all()
    ]


async def vendor_transactions(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    vendor_name: str,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Return paginated transactions for a specific vendor."""
    base_filter = and_(
        Transaction.workspace_id == workspace_id,
        func.lower(Transaction.vendor) == vendor_name.lower(),
    )
    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(Transaction).where(base_filter)
    )
    total = count_result.scalar() or 0

    # Paginated results
    result = await db.execute(
        select(Transaction)
        .where(base_filter)
        .order_by(Transaction.date.desc())
        .offset(skip)
        .limit(limit)
    )
    items = [
        {
            "id": str(t.id),
            "date": t.date.isoformat() if t.date else "",
            "description": t.description or "",
            "amount": float(t.amount or 0),
            "category": t.category or "",
            "type": t.type.value if t.type else "expense",
        }
        for t in result.scalars()
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# ═══════════════════════════════════════════════════════════════════
# VENDOR PERFORMANCE SCORING
# ═══════════════════════════════════════════════════════════════════

async def submit_review(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    vendor_id: uuid.UUID,
    reviewer_user_id: uuid.UUID,
    data: VendorReviewCreate,
) -> VendorReview:
    """Submit a performance review for a vendor."""
    review = VendorReview(
        workspace_id=workspace_id,
        vendor_id=vendor_id,
        reviewer_user_id=reviewer_user_id,
        delivery_rating=max(1, min(5, data.delivery_rating)),
        quality_rating=max(1, min(5, data.quality_rating)),
        responsiveness_rating=max(1, min(5, data.responsiveness_rating)),
        cost_rating=max(1, min(5, data.cost_rating)),
        comment=data.comment,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


async def list_reviews(
    db: AsyncSession, workspace_id: uuid.UUID, vendor_id: uuid.UUID
) -> list[VendorReview]:
    result = await db.execute(
        select(VendorReview).where(
            and_(VendorReview.workspace_id == workspace_id, VendorReview.vendor_id == vendor_id)
        ).order_by(VendorReview.review_date.desc())
    )
    return list(result.scalars())


async def get_vendor_scorecard(
    db: AsyncSession, workspace_id: uuid.UUID, vendor_id: uuid.UUID
) -> VendorScorecard | None:
    """Compute aggregate performance scorecard for a vendor."""
    vendor = await get_vendor(db, workspace_id, vendor_id)
    if not vendor:
        return None

    result = await db.execute(
        select(
            func.count(VendorReview.id),
            func.avg(VendorReview.delivery_rating),
            func.avg(VendorReview.quality_rating),
            func.avg(VendorReview.responsiveness_rating),
            func.avg(VendorReview.cost_rating),
        ).where(
            and_(VendorReview.workspace_id == workspace_id, VendorReview.vendor_id == vendor_id)
        )
    )
    row = result.one()
    total = int(row[0] or 0)
    if total == 0:
        return VendorScorecard(
            vendor_id=vendor_id, vendor_name=vendor.name,
            total_reviews=0, avg_delivery=0, avg_quality=0,
            avg_responsiveness=0, avg_cost=0, composite_score=0,
        )
    avg_d = round(float(row[1] or 0), 2)
    avg_q = round(float(row[2] or 0), 2)
    avg_r = round(float(row[3] or 0), 2)
    avg_c = round(float(row[4] or 0), 2)
    # Weighted composite: quality 30%, delivery 30%, responsiveness 20%, cost 20%
    composite = round(avg_q * 0.30 + avg_d * 0.30 + avg_r * 0.20 + avg_c * 0.20, 2)
    return VendorScorecard(
        vendor_id=vendor_id, vendor_name=vendor.name,
        total_reviews=total, avg_delivery=avg_d, avg_quality=avg_q,
        avg_responsiveness=avg_r, avg_cost=avg_c, composite_score=composite,
    )


# ═══════════════════════════════════════════════════════════════════
# VENDOR CONTRACT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

async def create_contract(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    vendor_id: uuid.UUID,
    data: ContractCreate,
) -> VendorContract:
    contract = VendorContract(
        workspace_id=workspace_id,
        vendor_id=vendor_id,
        title=data.title,
        contract_type=data.contract_type,
        start_date=data.start_date,
        end_date=data.end_date,
        value=data.value,
        auto_renew=data.auto_renew,
        renewal_notice_days=data.renewal_notice_days,
        notes=data.notes,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


async def list_contracts(
    db: AsyncSession, workspace_id: uuid.UUID, vendor_id: uuid.UUID
) -> list[VendorContract]:
    result = await db.execute(
        select(VendorContract).where(
            and_(VendorContract.workspace_id == workspace_id, VendorContract.vendor_id == vendor_id)
        ).order_by(VendorContract.end_date.asc())
    )
    return list(result.scalars())


async def get_contract(
    db: AsyncSession, workspace_id: uuid.UUID, contract_id: uuid.UUID
) -> VendorContract | None:
    return (await db.execute(
        select(VendorContract).where(
            and_(VendorContract.id == contract_id, VendorContract.workspace_id == workspace_id)
        )
    )).scalar_one_or_none()


async def update_contract(
    db: AsyncSession, contract: VendorContract, data: ContractUpdate
) -> VendorContract:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)
    await db.flush()
    await db.refresh(contract)
    return contract


async def get_expiring_contracts(
    db: AsyncSession, workspace_id: uuid.UUID, days_ahead: int = 30
) -> list[ContractExpiringSoon]:
    """Find contracts expiring within N days."""
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days_ahead)
    result = await db.execute(
        select(VendorContract, Vendor.name).join(
            Vendor, VendorContract.vendor_id == Vendor.id
        ).where(
            and_(
                VendorContract.workspace_id == workspace_id,
                VendorContract.status == ContractStatus.active,
                VendorContract.end_date <= deadline,
                VendorContract.end_date >= now,
            )
        ).order_by(VendorContract.end_date.asc())
    )
    rows = result.fetchall()
    expiring = []
    for contract, vendor_name in rows:
        days_remaining = (contract.end_date.replace(tzinfo=timezone.utc) - now).days if contract.end_date.tzinfo is None else (contract.end_date - now).days
        expiring.append(ContractExpiringSoon(
            contract=ContractOut.model_validate(contract),
            vendor_name=vendor_name,
            days_remaining=max(days_remaining, 0),
        ))
    return expiring
