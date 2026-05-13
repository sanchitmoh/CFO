"""
AI CFO — Transactions Router
CRUD, CSV upload with file storage & audit trail, pagination, and filtering.
"""
import csv
import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from schemas import TransactionCreate, TransactionOut, PaginatedTransactions
from services.audit_service import log_action
from services.exchange_rate_service import ExchangeRateService
from models import User, Transaction, TransactionType, FileUpload, FileUploadStatus, Workspace
from services.alert_engine import run_alert_engine
from services.embedding_service import embed_transaction
from services.file_storage import save_upload, compute_content_hash
from cache import invalidate_workspace_cache
from utils.sql_utils import escape_like
from services.budget_service import normalize_category_label

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
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = "date",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
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
        # SEC-CRIT-002: Escape SQL wildcards to prevent pattern injection
        filters.append(Transaction.description.ilike(f"%{escape_like(search)}%"))
    if start_date:
        filters.append(Transaction.date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(Transaction.date <= datetime.combine(end_date, datetime.max.time()))

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
    ws = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    base_currency = ws.currency if ws else "USD"

    amount_original = data.amount_original if data.amount_original is not None else data.amount
    currency_code = data.currency_code

    if data.exchange_rate is not None:
        exchange_rate = data.exchange_rate
        amount_base = amount_original * exchange_rate
    elif currency_code != base_currency:
        rate = await ExchangeRateService.get_exchange_rate(db, currency_code, base_currency, target_date=data.date)
        exchange_rate = float(rate)
        amount_base = amount_original * exchange_rate
    else:
        amount_base = amount_original
        exchange_rate = 1.0

    txn = Transaction(
        workspace_id=user.workspace_id,
        user_id=user.id,
        date=data.date,
        description=data.description,
        amount=amount_base,
        currency_code=currency_code,
        amount_original=amount_original,
        exchange_rate=exchange_rate,
        category=normalize_category_label(data.category),
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
        from database import get_rls_db_context
        async with get_rls_db_context(str(user.workspace_id)) as bg_db:
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

# ── Intelligent column mapping ────────────────────────────────────
# Maps common column name variations to our standard fields.
# NOTE: Checked in order — first match wins.  Keep the most specific
#       variations first within each list.
COLUMN_MAPPINGS: dict[str, list[str]] = {
    "date": [
        "date", "transaction date", "trans date", "posted date",
        "posting date", "dt", "transaction_date", "txn date",
        "trade date", "payment date", "invoice date",
    ],
    "amount": [
        "amount", "amount_inr", "amount_usd", "amount_eur", "amount_gbp",
        "transaction amount", "transaction_amount", "value", "total",
        "net amount", "gross amount", "sum", "price", "cost",
        "debit", "credit",
    ],
    "type": [
        "type", "transaction type", "trans type", "category type",
        "debit/credit", "dr/cr", "txn type",
    ],
    "description": [
        "description", "desc", "memo", "note", "notes", "details",
        "transaction description", "narration", "remarks", "particulars",
    ],
    "category": [
        "category", "cat", "expense category", "income category",
        "classification", "subcategory", "sub_category", "gl code",
    ],
    "account": [
        "account", "account name", "bank account", "acct",
        "account_name", "ledger",
    ],
    "vendor": [
        "vendor", "merchant", "payee", "supplier", "customer",
        "counterparty", "counter_party", "company", "party name",
        "beneficiary",
    ],
}

# Prefixes used in the fuzzy fallback pass (e.g. "amount_inr" starts with "amount")
_FIELD_PREFIXES: dict[str, list[str]] = {
    "amount": ["amount", "amt", "total", "value"],
    "date":   ["date", "dt"],
}


def auto_map_columns(csv_headers: list[str]) -> dict[str, str | None]:
    """Automatically map CSV column names to our standard fields.

    Pass 1 — exact match against the ``COLUMN_MAPPINGS`` alias lists.
    Pass 2 — for still-unmapped *required* fields, try a fuzzy prefix
    match (e.g. ``Amount_INR`` starts with ``amount``).

    Returns ``{"date": "Date", "amount": "Amount_INR", ...}``
    where values are the *original* header strings from the CSV.
    """
    header_lower = {h.strip().lower().replace(" ", "_"): h for h in csv_headers}
    # Also keep a version without underscores for space-delimited matching
    header_nospace = {h.strip().lower().replace("_", " "): h for h in csv_headers}
    mapping: dict[str, str | None] = {}

    # ── Pass 1: exact match ────────────────────────────────────────
    for standard_field, variations in COLUMN_MAPPINGS.items():
        for variation in variations:
            norm = variation.replace(" ", "_")
            if norm in header_lower:
                mapping[standard_field] = header_lower[norm]
                break
            if variation in header_nospace:
                mapping[standard_field] = header_nospace[variation]
                break
        if standard_field not in mapping:
            mapping[standard_field] = None

    # ── Pass 2: fuzzy prefix fallback for unmapped fields ──────────
    for field, prefixes in _FIELD_PREFIXES.items():
        if mapping.get(field) is not None:
            continue  # already resolved
        for col_lower, col_original in header_lower.items():
            for pfx in prefixes:
                if col_lower.startswith(pfx):
                    mapping[field] = col_original
                    break
            if mapping.get(field) is not None:
                break

    return mapping


@router.post("/upload-csv/preview")
async def preview_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Preview CSV file and suggest column mappings.
    Returns the first few rows and auto-detected column mappings.
    
    MED-009: Enforces MAX_CSV_BYTES size limit before processing.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")
    
    # MED-009: Read file content with size limit enforcement
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        # MED-009: Reject files exceeding size limit BEFORE parsing
        if total_bytes > MAX_CSV_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum allowed size is {MAX_CSV_BYTES // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    
    raw_content = b"".join(chunks)
    
    try:
        text = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")
    
    reader = csv.DictReader(io.StringIO(text))
    
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")
    
    # Get column headers
    headers = [h.strip() for h in reader.fieldnames]
    
    # Auto-detect column mappings
    suggested_mapping = auto_map_columns(headers)
    
    # Get first 5 rows as preview
    preview_rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        preview_rows.append({k.strip(): v.strip() if v else "" for k, v in row.items()})
    
    # Check which required columns are missing
    missing_required = []
    for req_col in REQUIRED_COLUMNS:
        if not suggested_mapping.get(req_col):
            missing_required.append(req_col)
    
    return {
        "filename": file.filename,
        "headers": headers,
        "suggested_mapping": suggested_mapping,
        "preview_rows": preview_rows,
        "missing_required": missing_required,
        "total_rows_estimate": text.count('\n') - 1,  # Rough estimate
    }


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    force: bool = Query(False, description="Skip duplicate detection"),
    column_mapping: str | None = Query(None, description="JSON string of column mappings, e.g. {'date':'Transaction Date','amount':'Amount'}"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Upload transactions from a CSV file with storage, audit trail, and validation.

    FILE-001: The original file is persisted to disk BEFORE parsing.
    A FileUpload record tracks every upload for audit, reprocessing,
    and duplicate detection via SHA-256 content hash.
    
    MED-009: Enforces MAX_CSV_BYTES (5MB) size limit to prevent memory exhaustion.
    
    Supports intelligent column mapping - if column_mapping is not provided,
    will attempt to auto-detect common column name variations.
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

    # ── 3. MED-009: Read with size cap (chunked to prevent OOM) ───
    # Reject files > MAX_CSV_BYTES (5MB) BEFORE parsing to prevent
    # memory exhaustion attacks via large file uploads.
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        # MED-009: Size limit enforcement - reject before processing
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

    # ── 8. Parse column mapping or auto-detect ────────────────────
    if reader.fieldnames is None:
        upload_record.status = FileUploadStatus.failed
        upload_record.error_details = {"reason": "Empty CSV or no header row"}
        await db.commit()
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    headers = [h.strip() for h in reader.fieldnames]
    
    # Parse provided mapping or auto-detect
    if column_mapping:
        import json
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")
    else:
        # Auto-detect column mappings
        mapping = auto_map_columns(headers)
    
    # Validate required columns are mapped
    missing = []
    for req_col in REQUIRED_COLUMNS:
        if not mapping.get(req_col) or mapping[req_col] not in headers:
            missing.append(req_col)
    
    if missing:
        upload_record.status = FileUploadStatus.failed
        upload_record.error_details = {
            "reason": f"Missing required columns: {sorted(missing)}",
            "available_headers": headers,
            "suggested_mapping": auto_map_columns(headers),
        }
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}. "
                   f"Available columns: {', '.join(headers)}. "
                   f"Use /upload-csv/preview to see suggested mappings.",
        )

    # ── 9. Parse & validate rows with row-count cap ───────────────
    count = 0
    errors: list[dict] = []
    batch: list[Transaction] = []

    # Fetch workspace base currency
    ws = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    base_currency = ws.currency if ws else "USD"
    exchange_rates_cache = {}

    for i, row in enumerate(reader):
        row_num = i + 2  # 1-indexed, +1 for header

        # Row count guard
        if (count + len(errors)) >= MAX_CSV_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"CSV exceeds maximum of {MAX_CSV_ROWS:,} rows. "
                       f"Please split the file into smaller batches.",
            )

        # Normalise keys and apply mapping
        row_normalized = {k.strip(): (v.strip() if v else "") for k, v in row.items()}
        
        # Map columns to our standard fields
        mapped_row = {}
        for standard_field, csv_column in mapping.items():
            if csv_column and csv_column in row_normalized:
                mapped_row[standard_field] = row_normalized[csv_column]
            else:
                mapped_row[standard_field] = ""

        # Validate date
        raw_date = mapped_row.get("date", "")
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            # Try other common date formats
            for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]:
                try:
                    parsed_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                errors.append({"row": row_num, "error": f"Invalid date '{raw_date}'. Expected YYYY-MM-DD or MM/DD/YYYY."})
                continue

        # Validate amount
        raw_amount = mapped_row.get("amount", "")
        currency_code = base_currency
        
        # Infer currency from the header mapped to "amount"
        amount_header = mapping.get("amount", "")
        if amount_header:
            upper_header = amount_header.upper()
            for iso in ["USD", "EUR", "GBP", "INR", "CAD", "AUD", "JPY", "SGD", "CHF"]:
                if iso in upper_header:
                    currency_code = iso
                    break

        try:
            # Remove currency symbols and commas
            clean_amount = raw_amount.replace(",", "").strip()
            if "€" in clean_amount: currency_code = "EUR"
            elif "£" in clean_amount: currency_code = "GBP"
            elif "₹" in clean_amount: currency_code = "INR"
            elif "¥" in clean_amount: currency_code = "JPY"
            elif "$" in clean_amount and currency_code not in ["CAD", "AUD", "SGD", "USD"]: 
                currency_code = "USD"
                
            clean_amount = clean_amount.replace("$", "").replace("£", "").replace("€", "").replace("₹", "").replace("¥", "").strip()
            amount_val = float(clean_amount)
            if amount_val <= 0:
                raise ValueError("must be positive")
        except ValueError:
            errors.append({"row": row_num, "error": f"Invalid amount '{raw_amount}'. Must be a positive number."})
            continue

        # Validate type
        raw_type = mapped_row.get("type", "").lower()
        # Auto-detect type if not provided or invalid
        if raw_type not in VALID_TYPES:
            # Try to infer from amount or other indicators
            if raw_amount.startswith("-") or "debit" in raw_type or "expense" in raw_type:
                raw_type = "expense"
            else:
                raw_type = "income"  # Default to income if unclear

        # Convert amount to base currency
        amount_original = amount_val
        if currency_code != base_currency:
            cache_key = (currency_code, parsed_date.date())
            if cache_key not in exchange_rates_cache:
                rate = await ExchangeRateService.get_exchange_rate(db, currency_code, base_currency, target_date=parsed_date.date())
                exchange_rates_cache[cache_key] = float(rate)
            exchange_rate = exchange_rates_cache[cache_key]
            amount_base = amount_original * exchange_rate
        else:
            amount_base = amount_original
            exchange_rate = 1.0

        txn = Transaction(
            workspace_id=user.workspace_id,
            user_id=user.id,
            date=parsed_date,
            description=mapped_row.get("description") or "CSV Import",
            amount=abs(amount_base),  # Always store as positive base currency
            currency_code=currency_code,
            amount_original=abs(amount_original),
            exchange_rate=exchange_rate,
            category=normalize_category_label(mapped_row.get("category") or "Uncategorized"),
            type=TransactionType(raw_type),
            account=mapped_row.get("account") or "Main Account",
            vendor=mapped_row.get("vendor") or None,
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
        from database import get_rls_db_context
        async with get_rls_db_context(str(user.workspace_id)) as bg_db:
            await run_alert_engine(bg_db, user.workspace_id)

    background_tasks.add_task(_run_alerts)

    # AUTO-SYNC: Create Vendor records from transaction vendor names
    async def _sync_vendors():
        from database import get_rls_db_context
        from services.vendor_service import sync_vendors_from_transactions
        async with get_rls_db_context(str(user.workspace_id)) as bg_db:
            await sync_vendors_from_transactions(bg_db, user.workspace_id)
            await bg_db.commit()

    background_tasks.add_task(_sync_vendors)

    return {
        "imported": count,
        "errors": errors[:50],  # Cap error output to avoid huge responses
        "total_rows": count + len(errors),
        "file_id": str(upload_record.id),
        "file_name": file.filename,
        "file_size": total_bytes,
        "duplicate_detected": False,
    }
