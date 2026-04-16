"""
AI CFO — Transactions Router
CRUD, CSV upload, pagination, and filtering.
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType
from schemas import TransactionCreate, TransactionOut, PaginatedTransactions
from services.audit_service import log_action
from cache import cache_delete

router = APIRouter()


@router.get("/", response_model=PaginatedTransactions)
async def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = None,
    type: str | None = None,
    search: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with filtering, sorting, and pagination."""
    ws_id = user.workspace_id
    base_filter = Transaction.workspace_id == ws_id

    filters = [base_filter]
    if category:
        filters.append(Transaction.category == category)
    if type:
        filters.append(Transaction.type == type)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))

    combined = and_(*filters)

    # Count
    count_q = await db.execute(
        select(func.count(Transaction.id)).where(combined)
    )
    total = count_q.scalar() or 0

    # Sort
    sort_col = getattr(Transaction, sort_by, Transaction.date)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Transaction)
        .where(combined)
        .order_by(order)
        .offset(offset)
        .limit(per_page)
    )
    items = [TransactionOut.model_validate(t) for t in result.scalars()]

    pages = (total + per_page - 1) // per_page

    return PaginatedTransactions(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new transaction."""
    txn = Transaction(
        workspace_id=user.workspace_id,
        user_id=user.id,
        date=data.date,
        description=data.description,
        amount=data.amount,
        category=data.category,
        type=TransactionType(data.type),
        account=data.account,
        vendor=data.vendor,
        notes=data.notes,
        source="manual",
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    # Invalidate dashboard cache
    await cache_delete(f"ws:{user.workspace_id}:dashboard:*")
    await log_action(db, user, "transaction.create", "transaction", txn.id)

    return TransactionOut.model_validate(txn)


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    txn_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction."""
    result = await db.execute(
        select(Transaction).where(
            and_(Transaction.id == txn_id, Transaction.workspace_id == user.workspace_id)
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await log_action(db, user, "transaction.delete", "transaction", txn.id)
    await db.delete(txn)
    await db.commit()
    await cache_delete(f"ws:{user.workspace_id}:dashboard:*")


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload transactions from a CSV file."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    errors = []
    for i, row in enumerate(reader):
        try:
            txn = Transaction(
                workspace_id=user.workspace_id,
                user_id=user.id,
                date=datetime.strptime(row.get("date", ""), "%Y-%m-%d"),
                description=row.get("description", "CSV Import"),
                amount=float(row.get("amount", 0)),
                category=row.get("category", "Uncategorized"),
                type=TransactionType(row.get("type", "expense")),
                account=row.get("account", "Main Account"),
                vendor=row.get("vendor"),
                source="csv",
            )
            db.add(txn)
            count += 1
        except Exception as e:
            errors.append({"row": i + 1, "error": str(e)})

    await db.commit()
    await cache_delete(f"ws:{user.workspace_id}:*")
    await log_action(db, user, "transaction.csv_upload", "transaction",
                     new_value={"count": count, "file": file.filename})

    return {
        "imported": count,
        "errors": errors,
        "total_rows": count + len(errors),
    }
