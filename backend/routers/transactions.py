"""
AI CFO — Transactions Router
CRUD, CSV upload, pagination, and filtering.
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_db_with_rls, get_db_context
from auth import get_current_user
from models import User, Transaction, TransactionType
from schemas import TransactionCreate, TransactionOut, PaginatedTransactions
from services.audit_service import log_action
from services.alert_engine import run_alert_engine
from services.embedding_service import embed_transaction
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
    db: AsyncSession = Depends(get_db),  # TODO(ADVANCE-004): Switch to RLS after Phase 2 testing
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
    background_tasks: BackgroundTasks,
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

    # ADVANCE-005: Generate embedding in background (non-blocking)
    async def _embed():
        async with get_db_context() as bg_db:
            await embed_transaction(
                txn.id, txn.description, txn.category, txn.vendor, bg_db
            )
    background_tasks.add_task(_embed)

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


# ── CSV Upload constraints ────────────────────────────────────────
MAX_CSV_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_CSV_ROWS = 5_000
CHUNK_SIZE = 64 * 1024            # 64 KB read chunks
ALLOWED_MIME_TYPES = {"text/csv", "application/octet-stream", "text/plain"}
REQUIRED_COLUMNS = {"date", "amount", "type"}
VALID_TYPES = {"income", "expense"}
BATCH_SIZE = 500


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload transactions from a CSV file with full validation."""

    # ── 1. Filename extension ─────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    # ── 2. MIME type ──────────────────────────────────────────────
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Expected text/csv.",
        )

    # ── 3. Read with size cap (chunked to prevent OOM) ────────────
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_CSV_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum allowed size is {MAX_CSV_BYTES // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)

    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")

    reader = csv.DictReader(io.StringIO(text))

    # ── 4. Validate required columns ──────────────────────────────
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    header_set = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header_set
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: {', '.join(sorted(REQUIRED_COLUMNS))}.",
        )

    # ── 5. Parse & validate rows with row-count cap ───────────────
    count = 0
    errors: list[dict] = []
    batch: list[Transaction] = []

    for i, row in enumerate(reader):
        row_num = i + 2  # 1-indexed, +1 for header

        # Row count guard
        if (count + len(errors)) >= MAX_CSV_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"CSV exceeds maximum of {MAX_CSV_ROWS:,} rows. "
                       f"Please split the file into smaller batches.",
            )

        # Normalise keys
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

        # Validate date
        raw_date = row.get("date", "")
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid date '{raw_date}'. Expected YYYY-MM-DD."})
            continue

        # Validate amount
        raw_amount = row.get("amount", "")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError("must be positive")
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid amount '{raw_amount}'. Must be a positive number."})
            continue

        # Validate type
        raw_type = row.get("type", "").lower()
        if raw_type not in VALID_TYPES:
            errors.append({"row": row_num, "error": f"Invalid type '{raw_type}'. Must be 'income' or 'expense'."})
            continue

        txn = Transaction(
            workspace_id=user.workspace_id,
            user_id=user.id,
            date=parsed_date,
            description=row.get("description") or "CSV Import",
            amount=amount,
            category=row.get("category") or "Uncategorized",
            type=TransactionType(raw_type),
            account=row.get("account") or "Main Account",
            vendor=row.get("vendor") or None,
            source="csv",
        )
        batch.append(txn)
        count += 1

        # Flush batch to DB periodically
        if len(batch) >= BATCH_SIZE:
            db.add_all(batch)
            await db.flush()
            batch.clear()

    # Flush remaining
    if batch:
        db.add_all(batch)

    await db.commit()
    await cache_delete(f"ws:{user.workspace_id}:*")
    await log_action(db, user, "transaction.csv_upload", "transaction",
                     new_value={"count": count, "file": file.filename})

    # ARCH-004: Trigger alert checks in the background after data mutation
    async def _run_alerts():
        async with get_db_context() as bg_db:
            await run_alert_engine(bg_db, user.workspace_id)

    background_tasks.add_task(_run_alerts)

    return {
        "imported": count,
        "errors": errors[:50],  # Cap error output to avoid huge responses
        "total_rows": count + len(errors),
    }
