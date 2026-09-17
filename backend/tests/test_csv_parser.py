"""
Unit tests for the upgraded CSV parse engine.
Tests all transaction types, column mappings, dual-column debit/credit,
parentheses amounts, negative amounts, categories, and vendor extraction.
"""
import io
import csv
import re
from datetime import datetime
import pytest
from models import TransactionType
from routers.transactions import (
    auto_map_columns, COLUMN_MAPPINGS, TYPE_SYNONYMS, VALID_TYPES,
    REQUIRED_COLUMNS,
)
from services.budget_service import normalize_category_label


def test_transaction_type_enum_values():
    """Verify all required transaction types exist in the model enum."""
    assert TransactionType.income == "income"
    assert TransactionType.expense == "expense"
    assert TransactionType.credit == "credit"
    assert TransactionType.debit == "debit"
    assert TransactionType.transfer == "transfer"
    assert TransactionType.refund == "refund"


def test_valid_types_contains_all():
    """Verify VALID_TYPES set contains all supported types."""
    expected = {"income", "expense", "credit", "debit", "transfer", "refund"}
    assert expected.issubset(VALID_TYPES)


def test_required_columns_does_not_mandate_type():
    """Verify type is optional in CSV headers (auto-inferred if absent)."""
    assert "type" not in REQUIRED_COLUMNS
    assert "date" in REQUIRED_COLUMNS
    assert "amount" in REQUIRED_COLUMNS


def test_type_synonyms():
    """Verify common banking abbreviations map to expected types."""
    assert TYPE_SYNONYMS["dr"] == "debit"
    assert TYPE_SYNONYMS["cr"] == "credit"
    assert TYPE_SYNONYMS["deposit"] == "credit"
    assert TYPE_SYNONYMS["withdrawal"] == "debit"
    assert TYPE_SYNONYMS["payment"] == "expense"
    assert TYPE_SYNONYMS["payout"] == "expense"
    assert TYPE_SYNONYMS["charge"] == "debit"
    assert TYPE_SYNONYMS["refund"] == "refund"
    assert TYPE_SYNONYMS["transfer"] == "transfer"


def test_auto_map_columns_standard():
    """Test standard header mapping."""
    headers = ["Date", "Description", "Amount", "Type", "Category", "Vendor"]
    mapping = auto_map_columns(headers)
    assert mapping["date"] == "Date"
    assert mapping["description"] == "Description"
    assert mapping["amount"] == "Amount"
    assert mapping["type"] == "Type"
    assert mapping["category"] == "Category"
    assert mapping["vendor"] == "Vendor"


def test_auto_map_columns_variations():
    """Test mapping with various real-world bank header names."""
    headers = [
        "Transaction Date", "Particulars", "Net Amount",
        "Trans Type", "Cost Center", "Merchant Name"
    ]
    mapping = auto_map_columns(headers)
    assert mapping["date"] == "Transaction Date"
    assert mapping["description"] == "Particulars"
    assert mapping["amount"] == "Net Amount"
    assert mapping["type"] == "Trans Type"
    assert mapping["category"] == "Cost Center"
    assert mapping["vendor"] == "Merchant Name"


def test_auto_map_columns_payee_and_group():
    """Test mapping with Payee and Group."""
    headers = ["Posted Date", "Narration", "Total", "Payee", "Group"]
    mapping = auto_map_columns(headers)
    assert mapping["date"] == "Posted Date"
    assert mapping["description"] == "Narration"
    assert mapping["amount"] == "Total"
    assert mapping["vendor"] == "Payee"
    assert mapping["category"] == "Group"


def test_auto_map_columns_fuzzy_prefixes():
    """Test fuzzy prefix fallback (e.g. Amount_INR, Cat_Type)."""
    headers = ["date_time", "amount_inr", "cat_name", "vendor_id_code"]
    mapping = auto_map_columns(headers)
    assert mapping["date"] == "date_time"
    assert mapping["amount"] == "amount_inr"
    assert mapping["category"] == "cat_name"
    assert mapping["vendor"] == "vendor_id_code"


def parse_csv_rows_simulated(csv_text: str):
    """Simulate the parsing loop in upload_csv for testing field extraction."""
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    headers = [h.strip() for h in reader.fieldnames]
    mapping = auto_map_columns(headers)
    results = []

    DATE_FORMATS = [
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%m-%d-%Y", "%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    ]

    for row in reader:
        row_normalized = {k.strip(): (v.strip() if v else "") for k, v in row.items()}
        mapped_row = {f: row_normalized.get(mapping.get(f) or "", "") for f in mapping}

        # Date
        raw_date = mapped_row.get("date", "").strip()
        parsed_date = None
        clean_date_str = raw_date.split("T")[0].split(" ")[0].strip() if ("T" in raw_date or " " in raw_date) else raw_date
        for fmt in DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(raw_date, fmt)
                break
            except ValueError:
                pass
            if clean_date_str != raw_date:
                try:
                    parsed_date = datetime.strptime(clean_date_str, fmt)
                    break
                except ValueError:
                    pass

        # Dual column debit / credit
        debit_col = None
        credit_col = None
        for col_name in row_normalized.keys():
            clow = col_name.lower().replace(" ", "_")
            if clow in ("debit", "debit_amount", "withdrawal", "withdrawals", "dr", "money_out", "spent"):
                debit_col = col_name
            elif clow in ("credit", "credit_amount", "deposit", "deposits", "cr", "money_in", "received"):
                credit_col = col_name

        raw_amount = mapped_row.get("amount", "")
        inferred_type = None

        if debit_col and credit_col:
            raw_deb = row_normalized.get(debit_col, "").strip()
            raw_crd = row_normalized.get(credit_col, "").strip()
            val_deb = abs(float(re.sub(r"[^\d\.-]", "", raw_deb))) if raw_deb else 0.0
            val_crd = abs(float(re.sub(r"[^\d\.-]", "", raw_crd))) if raw_crd else 0.0
            if val_deb > 0 and val_crd == 0:
                raw_amount = raw_deb
                inferred_type = "debit"
            elif val_crd > 0 and val_deb == 0:
                raw_amount = raw_crd
                inferred_type = "credit"

        clean_amount = str(raw_amount).replace(",", "").strip()
        is_negative = False
        if clean_amount.startswith("(") and clean_amount.endswith(")"):
            is_negative = True
            clean_amount = clean_amount[1:-1].strip()
        if clean_amount.startswith("-"):
            is_negative = True
            clean_amount = clean_amount[1:].strip()
        elif clean_amount.endswith("-"):
            is_negative = True
            clean_amount = clean_amount[:-1].strip()

        clean_num = re.sub(r"[^\d\.]", "", clean_amount)
        amount_val = abs(float(clean_num))

        # Type resolution
        raw_type = mapped_row.get("type", "").lower().strip()
        final_type = None
        if raw_type in TYPE_SYNONYMS:
            final_type = TYPE_SYNONYMS[raw_type]
        elif raw_type in VALID_TYPES:
            final_type = raw_type
        else:
            for syn_k, syn_v in TYPE_SYNONYMS.items():
                if syn_k in raw_type:
                    final_type = syn_v
                    break

        if not final_type and inferred_type:
            final_type = inferred_type

        if not final_type:
            final_type = "expense" if is_negative else "income"

        vendor_val = mapped_row.get("vendor") or None
        if vendor_val:
            vendor_val = vendor_val.strip() or None

        cat_val = mapped_row.get("category") or "Uncategorized"
        cat_clean = normalize_category_label(cat_val)

        results.append({
            "date": parsed_date,
            "amount": amount_val,
            "type": final_type,
            "category": cat_clean,
            "vendor": vendor_val,
        })

    return results


def test_parse_multi_types_and_synonyms():
    """Verify parser extracts expense, income, credit, debit, transfer, refund, dr, cr."""
    csv_data = """Date,Description,Amount,Type,Category,Vendor
2026-03-01,Office Supplies,50.00,expense,Office,Staples
2026-03-02,Client Retainer,2500.00,income,Services,Acme Corp
2026-03-03,Wire In,1000.00,credit,Capital,Venture Fund
2026-03-04,Server Hosting,120.00,debit,Infrastructure,AWS
2026-03-05,Checking to Savings,500.00,transfer,Transfer,Chase
2026-03-06,Damaged Goods Return,45.00,refund,Refunds,Amazon
2026-03-07,ATM Withdrawal,100.00,DR,Cash,ATM
2026-03-08,Customer Deposit,750.00,CR,Revenue,Client X
"""
    rows = parse_csv_rows_simulated(csv_data)
    assert len(rows) == 8
    assert rows[0]["type"] == "expense"
    assert rows[0]["vendor"] == "Staples"
    assert rows[0]["category"] == "Office"

    assert rows[1]["type"] == "income"
    assert rows[1]["vendor"] == "Acme Corp"

    assert rows[2]["type"] == "credit"
    assert rows[2]["amount"] == 1000.00

    assert rows[3]["type"] == "debit"
    assert rows[3]["vendor"] == "AWS"

    assert rows[4]["type"] == "transfer"
    assert rows[5]["type"] == "refund"
    assert rows[6]["type"] == "debit"
    assert rows[7]["type"] == "credit"


def test_parse_negative_and_parentheses_amounts():
    """Verify negative amounts and (100.00) are parsed as positive values with expense type."""
    csv_data = """Date,Description,Amount,Category,Vendor
2026-03-10,Software Sub,-99.00,Software,Figma
2026-03-11,Hardware Purchase,(450.00),Equipment,Apple
2026-03-12,Client Payment,1500.00,Income,Globex
"""
    rows = parse_csv_rows_simulated(csv_data)
    assert len(rows) == 3
    assert rows[0]["amount"] == 99.00
    assert rows[0]["type"] == "expense"
    assert rows[0]["vendor"] == "Figma"

    assert rows[1]["amount"] == 450.00
    assert rows[1]["type"] == "expense"
    assert rows[1]["vendor"] == "Apple"

    assert rows[2]["amount"] == 1500.00
    assert rows[2]["type"] == "income"


def test_parse_dual_column_debit_credit():
    """Verify bank CSVs with separate Debit and Credit columns are handled."""
    csv_data = """Date,Particulars,Debit,Credit,Payee,Group
2026-03-01,Cloud Server,250.00,,AWS,Tech
2026-03-02,Client Deposit,,5000.00,Google,Sales
"""
    rows = parse_csv_rows_simulated(csv_data)
    assert len(rows) == 2
    assert rows[0]["amount"] == 250.00
    assert rows[0]["type"] == "debit"
    assert rows[0]["vendor"] == "AWS"
    assert rows[0]["category"] == "Tech"

    assert rows[1]["amount"] == 5000.00
    assert rows[1]["type"] == "credit"
    assert rows[1]["vendor"] == "Google"
    assert rows[1]["category"] == "Sales"


def test_parse_currency_symbols():
    """Verify amounts with $, EUR, GBP, INR symbols are cleaned properly."""
    csv_data = """Date,Description,Amount,Type,Category,Vendor
2026-03-01,Item 1,"$1,500.50",expense,General,Store A
2026-03-02,Item 2,"₹45,000.00",debit,Supplies,Supplier B
2026-03-03,Item 3,"£320.00",expense,Logistics,Courier C
"""
    rows = parse_csv_rows_simulated(csv_data)
    assert len(rows) == 3
    assert rows[0]["amount"] == 1500.50
    assert rows[1]["amount"] == 45000.00
    assert rows[2]["amount"] == 320.00
