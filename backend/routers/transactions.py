"""
AI CFO — Transactions Router
CRUD, CSV upload with file storage & audit trail, pagination, and filtering.
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_context
from dependencies import get_rls_db
from auth import get_current_user
from models import User, Transaction, TransactionType, FileUpload, FileUploadStatus
from schemas import TransactionCreate, TransactionOut, PaginatedTransactions
from services.audit_service import log_action
from services.alert_engine import run_alert_engine
from services.embedding_service import embed_transaction
from services.file_storage import save_upload, compute_content_hash
from cache import invalidate_workspace_cache

router = APIRouter()

# SEC-007: Explicit allowlist for sort columns — prevents attribute injection
ALLOWED_SORT_COLUMNS = {"date", "amount", "category", "description", "created_at", "type", "vendor"}


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
    db: AsyncSession = Depends(get_rls_db),
):
    """List transactions with filtering, sorting, and pagination."""
    # SEC-007: Validate sort_by against allowlist before getattr
    if sort_by not in ALLOWED_SORT_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_by}'. Allowed: {sorted(ALLOWED_SORT_COLUMNS)}",
        )

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

    # Sort — safe after allowlist check above
    sort_col = getattr(Transaction, sort_by)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    # PERF-003: Single query with window function for count + rows
    offset = (page - 1) * per_page
    window_count = func.count(Transaction.id).over().label("total_count")
    result = await db.execute(
        select(Transaction, window_count)
        .where(combined)
        .order_by(order)
        .offset(offset)
        .limit(per_page)
    )
    rows = result.all()

    # Extract total from window function (same value on every row)
    total = rows[0].total_count if rows else 0
    items = [TransactionOut.model_validate(r[0]) for r in rows]

    pages = (total + per_page - 1) // per_page

    return PaginatedTransactions(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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

    # PERF-002: O(1) version bump instead of scanning/deleting cache keys
    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "transaction.create", "transaction", txn.id)

    # ADVANCE-005: Generate embedding in background (non-blocking)
    async def _embed():
        async with get_db_context() as bg_db:
            await embed_transaction(
                txn.id, txn.description, txn.category, txn.vendor, bg_db,
                workspace_id=user.workspace_id,  # M-005: tenant isolation
            )
    background_tasks.add_task(_embed)

    return TransactionOut.model_validate(txn)


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    txn_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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
    await invalidate_workspace_cache(str(user.workspace_id))


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
    force: bool = Query(False, description="Skip duplicate detection"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Upload transactions from a CSV file with storage, audit trail, and validation.

    FILE-001: The original file is persisted to disk BEFORE parsing.
    A FileUpload record tracks every upload for audit, reprocessing,
    and duplicate detection via SHA-256 content hash.
    """

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

    raw_content = b"".join(chunks)

    # ── 4. FILE-001: Duplicate detection via SHA-256 ──────────────
    content_hash = await compute_content_hash(raw_content)
    if not force:
        dup_check = await db.execute(
            select(FileUpload.id).where(
                and_(
                    FileUpload.workspace_id == user.workspace_id,
                    FileUpload.content_hash == content_hash,
                    FileUpload.status == FileUploadStatus.processed,
                )
            )
        )
        existing = dup_check.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"This file has already been uploaded (upload ID: {existing}). "
                       f"Use ?force=true to upload anyway.",
            )

    # ── 5. FILE-001: Store original file to disk FIRST ────────────
    storage_path = await save_upload(
        workspace_id=user.workspace_id,
        filename=file.filename,
        content=raw_content,
    )

    # ── 6. FILE-001: Create FileUpload audit record ───────────────
    upload_record = FileUpload(
        workspace_id=user.workspace_id,
        user_id=user.id,
        filename=file.filename,
        file_size=total_bytes,
        content_hash=content_hash,
        storage_path=storage_path,
        status=FileUploadStatus.pending,
    )
    db.add(upload_record)
    await db.flush()  # get the ID before commit

    # ── 7. Decode and parse CSV ───────────────────────────────────
    try:
        text = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        upload_record.status = FileUploadStatus.failed
        upload_record.error_details = {"reason": "File is not valid UTF-8 text"}
        await db.commit()
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")

    reader = csv.DictReader(io.StringIO(text))

    # ── 8. Validate required columns ──────────────────────────────
    if reader.fieldnames is None:
        upload_record.status = FileUploadStatus.failed
        upload_record.error_details = {"reason": "Empty CSV or no header row"}
        await db.commit()
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    header_set = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header_set
    if missing:
        upload_record.status = FileUploadStatus.failed
        upload_record.error_details = {"reason": f"Missing columns: {sorted(missing)}"}
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: {', '.join(sorted(REQUIRED_COLUMNS))}.",
        )

    # ── 9. Parse & validate rows with row-count cap ───────────────
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

    # ── 10. FILE-001: Update FileUpload record with results ───────
    upload_record.row_count = count
    upload_record.error_count = len(errors)
    upload_record.status = FileUploadStatus.processed
    if errors:
        upload_record.error_details = {"errors": errors[:50]}

    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "transaction.csv_upload", "transaction",
                     new_value={"count": count, "file": file.filename,
                                "file_upload_id": str(upload_record.id)})

    # ARCH-004: Trigger alert checks in the background after data mutation
    async def _run_alerts():
        async with get_db_context() as bg_db:
            await run_alert_engine(bg_db, user.workspace_id)

    background_tasks.add_task(_run_alerts)

    return {
        "imported": count,
        "errors": errors[:50],  # Cap error output to avoid huge responses
        "total_rows": count + len(errors),
        "file_id": str(upload_record.id),
        "file_name": file.filename,
        "file_size": total_bytes,
        "duplicate_detected": False,
    }
