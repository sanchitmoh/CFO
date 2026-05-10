"""
AI CFO — Tax Management Service
Tax category mapping, quarterly estimates (India + US), and report generation.
"""
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    TaxCategory, TaxEstimate, TaxJurisdiction,
    Transaction, TransactionType, TaxDeductibility, TaxEstimateStatus,
)

logger = logging.getLogger(__name__)

# India / US Tax Rate Slabs
_INDIA_TAX_SLABS = [
    (300000, Decimal("0.00")), (700000, Decimal("0.05")),
    (1000000, Decimal("0.10")), (1200000, Decimal("0.15")),
    (1500000, Decimal("0.20")), (float("inf"), Decimal("0.30")),
]
_US_TAX_SLABS = [
    (11600, Decimal("0.10")), (47150, Decimal("0.12")),
    (100525, Decimal("0.22")), (191950, Decimal("0.24")),
    (243725, Decimal("0.32")), (609350, Decimal("0.35")),
    (float("inf"), Decimal("0.37")),
]

def _compute_slab_tax(taxable: Decimal, jurisdiction: str) -> Decimal:
    slabs = _INDIA_TAX_SLABS if jurisdiction == "IN" else _US_TAX_SLABS
    tax, prev = Decimal("0"), 0
    remaining = float(taxable)
    for limit, rate in slabs:
        if remaining <= 0: break
        bracket = min(remaining, limit - prev)
        tax += Decimal(str(bracket)) * rate
        remaining -= bracket
        prev = limit
    return tax.quantize(Decimal("0.01"))

def _quarter_date_range(q_str: str):
    year, q = q_str.split("-Q"); year, q = int(year), int(q)
    ms = (q - 1) * 3 + 1
    start = datetime(year, ms, 1, tzinfo=timezone.utc)
    me = ms + 3
    end = datetime(year + 1, me - 12, 1, tzinfo=timezone.utc) if me > 12 else datetime(year, me, 1, tzinfo=timezone.utc)
    return start, end

def _quarter_due_date(q_str: str, jur: str) -> datetime:
    year, q = q_str.split("-Q"); year, q = int(year), int(q)
    if jur == "IN":
        dm = {1: 6, 2: 9, 3: 12, 4: 3}
    else:
        dm = {1: 4, 2: 6, 3: 9, 4: 1}
    m = dm.get(q, 6); y = year + 1 if q == 4 else year
    return datetime(y, m, 15, tzinfo=timezone.utc)

async def list_tax_categories(db: AsyncSession, ws_id: uuid.UUID, jur: str | None = None) -> list[TaxCategory]:
    q = select(TaxCategory).where(TaxCategory.workspace_id == ws_id)
    if jur: q = q.where(TaxCategory.jurisdiction == jur)
    return list((await db.execute(q.order_by(TaxCategory.category))).scalars())

async def create_tax_category(db: AsyncSession, ws_id: uuid.UUID, data) -> TaxCategory:
    cat = TaxCategory(workspace_id=ws_id, category=data.category, tax_code=data.tax_code,
                       deduction_rate=Decimal(str(data.deduction_rate)), jurisdiction=data.jurisdiction, notes=data.notes)
    db.add(cat); await db.flush(); await db.refresh(cat); return cat

async def list_tax_estimates(db: AsyncSession, ws_id: uuid.UUID) -> list[TaxEstimate]:
    return list((await db.execute(select(TaxEstimate).where(TaxEstimate.workspace_id == ws_id).order_by(TaxEstimate.quarter.desc()))).scalars())

async def compute_quarterly_estimate(db: AsyncSession, ws_id: uuid.UUID, data) -> TaxEstimate:
    start, end = _quarter_date_range(data.quarter)
    income = Decimal(str((await db.execute(select(func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.income,
        Transaction.date >= start, Transaction.date < end)))).scalar() or 0))
    expense = Decimal(str((await db.execute(select(func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.expense,
        Transaction.date >= start, Transaction.date < end)))).scalar() or 0))
    tax_cats = await list_tax_categories(db, ws_id, data.jurisdiction)
    cat_map = {tc.category: tc for tc in tax_cats}
    cat_q = await db.execute(select(Transaction.category, func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.expense,
        Transaction.date >= start, Transaction.date < end)).group_by(Transaction.category))
    deductions = Decimal("0")
    for row in cat_q:
        tc = cat_map.get(row[0])
        if tc and tc.tax_code in (TaxDeductibility.deductible, TaxDeductibility.partially_deductible):
            deductions += Decimal(str(row[1] or 0)) * (tc.deduction_rate / Decimal("100"))
    taxable = max(income - deductions, Decimal("0"))
    est_tax = _compute_slab_tax(taxable, data.jurisdiction)
    eff_rate = (est_tax / taxable).quantize(Decimal("0.0001")) if taxable > 0 else Decimal("0")
    existing = (await db.execute(select(TaxEstimate).where(and_(
        TaxEstimate.workspace_id == ws_id, TaxEstimate.quarter == data.quarter,
        TaxEstimate.jurisdiction == data.jurisdiction)))).scalar_one_or_none()
    if existing:
        existing.taxable_income = taxable; existing.estimated_tax = est_tax
        existing.effective_rate = eff_rate; existing.deductions_total = deductions
        existing.due_date = _quarter_due_date(data.quarter, data.jurisdiction)
        estimate = existing
    else:
        estimate = TaxEstimate(workspace_id=ws_id, quarter=data.quarter, jurisdiction=data.jurisdiction,
            taxable_income=taxable, estimated_tax=est_tax, effective_rate=eff_rate,
            deductions_total=deductions, due_date=_quarter_due_date(data.quarter, data.jurisdiction))
        db.add(estimate)
    await db.flush(); await db.refresh(estimate); return estimate

async def seed_default_tax_data(db: AsyncSession, ws_id: uuid.UUID) -> None:
    """Seed default jurisdictions + common tax categories for a new workspace.
    Idempotent — skips if data already exists."""
    existing = (await db.execute(
        select(TaxJurisdiction).where(TaxJurisdiction.workspace_id == ws_id).limit(1)
    )).scalar_one_or_none()
    if existing:
        return  # Already seeded

    # Default jurisdictions — comprehensive tax data for filing assistance
    _default_jurisdictions = [
        {"name": "India", "code": "IN", "filing_frequency": "quarterly",
         "tax_rates_json": {
             "regime": "new_regime",
             "assessment_year": "2027-28",
             "financial_year": "2026-27",
             "currency": "INR",
             "standard_deduction": 75000,
             "slabs": [
                 {"min": 0,       "max": 400000,  "rate": 0.00, "label": "Nil"},
                 {"min": 400001,  "max": 800000,  "rate": 0.05, "label": "5%"},
                 {"min": 800001,  "max": 1200000, "rate": 0.10, "label": "10%"},
                 {"min": 1200001, "max": 1600000, "rate": 0.15, "label": "15%"},
                 {"min": 1600001, "max": 2000000, "rate": 0.20, "label": "20%"},
                 {"min": 2000001, "max": 2400000, "rate": 0.25, "label": "25%"},
                 {"min": 2400001, "max": None,     "rate": 0.30, "label": "30%"},
             ],
             "surcharge": [
                 {"min": 0,        "max": 5000000,  "rate": 0.00, "label": "Nil"},
                 {"min": 5000001,  "max": 10000000, "rate": 0.10, "label": "10% surcharge"},
                 {"min": 10000001, "max": 20000000, "rate": 0.15, "label": "15% surcharge"},
                 {"min": 20000001, "max": 50000000, "rate": 0.25, "label": "25% surcharge"},
                 {"min": 50000001, "max": None,      "rate": 0.25, "label": "25% (capped for new regime)"},
             ],
             "cess": {"rate": 0.04, "label": "Health & Education Cess @ 4% on tax + surcharge"},
             "rebate_87a": {"limit": 1200000, "max_rebate": 60000, "note": "Full tax rebate if taxable income ≤ ₹12L under new regime"},
             "tds_rates": {
                 "salary": "As per slab",
                 "interest_10A": {"threshold": 40000, "rate": 0.10, "senior_threshold": 50000},
                 "rent_194I": {"threshold": 240000, "rate_land": 0.10, "rate_equipment": 0.02},
                 "professional_194J": {"threshold": 30000, "rate": 0.10},
                 "contractor_194C": {"rate_individual": 0.01, "rate_company": 0.02, "threshold": 30000},
                 "commission_194H": {"threshold": 15000, "rate": 0.05},
             },
             "key_deductions": {
                 "80C": {"limit": 150000, "items": ["PPF", "ELSS", "Life Insurance", "NSC", "Tuition Fees", "EPF", "Home Loan Principal"]},
                 "80CCD_1B": {"limit": 50000, "items": ["NPS additional"]},
                 "80D": {"self_limit": 25000, "senior_limit": 50000, "parents_limit": 25000, "parents_senior_limit": 50000, "items": ["Health Insurance", "Preventive Health Checkup (₹5000)"]},
                 "80TTA": {"limit": 10000, "items": ["Savings account interest"]},
                 "80E": {"limit": None, "items": ["Education loan interest (full deduction)"]},
                 "24b": {"limit": 200000, "items": ["Home loan interest (self-occupied)"]},
                 "HRA": {"note": "Least of: actual HRA, 50%/40% of salary, rent - 10% salary"},
                 "note": "80C/80D etc. available ONLY under old regime. New regime allows only std deduction + NPS employer."
             },
             "gst_rates": [
                 {"rate": 0.00, "items": ["Essential food grains", "Fresh fruits & vegetables", "Milk", "Education", "Healthcare"]},
                 {"rate": 0.05, "items": ["Packaged food", "Transport", "Small restaurants"]},
                 {"rate": 0.12, "items": ["Business class restaurants", "Processed food", "Mobile phones"]},
                 {"rate": 0.18, "items": ["Most services", "IT services", "Financial services", "Restaurants in hotels >₹7500"]},
                 {"rate": 0.28, "items": ["Luxury goods", "Automobiles", "Tobacco", "Aerated drinks"]},
             ],
             "advance_tax_schedule": [
                 {"due_date": "June 15", "cumulative_pct": 15, "label": "Q1 — at least 15% of annual tax"},
                 {"due_date": "September 15", "cumulative_pct": 45, "label": "Q2 — at least 45% of annual tax"},
                 {"due_date": "December 15", "cumulative_pct": 75, "label": "Q3 — at least 75% of annual tax"},
                 {"due_date": "March 15", "cumulative_pct": 100, "label": "Q4 — 100% of annual tax"},
             ],
             "filing_deadlines": {
                 "ITR_individual": "July 31",
                 "ITR_audit": "October 31",
                 "ITR_transfer_pricing": "November 30",
                 "belated_return": "December 31",
                 "revised_return": "December 31",
             },
             "penalties": {
                 "late_filing": {"before_dec31": 5000, "after_dec31": 10000, "income_under_5L": 1000},
                 "interest_234A": "1% per month on unpaid tax (late filing)",
                 "interest_234B": "1% per month on shortfall of advance tax",
                 "interest_234C": "1% per month on deferred advance tax installment",
             },
         }},
        {"name": "United States", "code": "US", "filing_frequency": "quarterly",
         "tax_rates_json": {
             "tax_year": 2026,
             "currency": "USD",
             "standard_deduction": {
                 "single": 15700,
                 "married_filing_jointly": 31400,
                 "married_filing_separately": 15700,
                 "head_of_household": 23500,
             },
             "slabs_single": [
                 {"min": 0,      "max": 11925,  "rate": 0.10, "label": "10%"},
                 {"min": 11926,  "max": 48475,  "rate": 0.12, "label": "12%"},
                 {"min": 48476,  "max": 103350, "rate": 0.22, "label": "22%"},
                 {"min": 103351, "max": 197300, "rate": 0.24, "label": "24%"},
                 {"min": 197301, "max": 250525, "rate": 0.32, "label": "32%"},
                 {"min": 250526, "max": 626350, "rate": 0.35, "label": "35%"},
                 {"min": 626351, "max": None,    "rate": 0.37, "label": "37%"},
             ],
             "slabs_married_jointly": [
                 {"min": 0,      "max": 23850,  "rate": 0.10, "label": "10%"},
                 {"min": 23851,  "max": 96950,  "rate": 0.12, "label": "12%"},
                 {"min": 96951,  "max": 206700, "rate": 0.22, "label": "22%"},
                 {"min": 206701, "max": 394600, "rate": 0.24, "label": "24%"},
                 {"min": 394601, "max": 501050, "rate": 0.32, "label": "32%"},
                 {"min": 501051, "max": 751600, "rate": 0.35, "label": "35%"},
                 {"min": 751601, "max": None,    "rate": 0.37, "label": "37%"},
             ],
             "slabs_head_of_household": [
                 {"min": 0,      "max": 17000,  "rate": 0.10, "label": "10%"},
                 {"min": 17001,  "max": 64850,  "rate": 0.12, "label": "12%"},
                 {"min": 64851,  "max": 103350, "rate": 0.22, "label": "22%"},
                 {"min": 103351, "max": 197300, "rate": 0.24, "label": "24%"},
                 {"min": 197301, "max": 250500, "rate": 0.32, "label": "32%"},
                 {"min": 250501, "max": 626350, "rate": 0.35, "label": "35%"},
                 {"min": 626351, "max": None,    "rate": 0.37, "label": "37%"},
             ],
             "amt": {"exemption_single": 85700, "exemption_mfj": 133300, "rate": 0.26, "high_rate": 0.28, "high_threshold": 239100},
             "self_employment_tax": {
                 "social_security_rate": 0.124,
                 "social_security_wage_base": 176100,
                 "medicare_rate": 0.029,
                 "additional_medicare_rate": 0.009,
                 "additional_medicare_threshold_single": 200000,
                 "deductible_half": True,
             },
             "capital_gains": {
                 "short_term": "Taxed as ordinary income",
                 "long_term_rates": [
                     {"min": 0,      "max": 48350,  "rate": 0.00, "filing": "single"},
                     {"min": 48351,  "max": 533400, "rate": 0.15, "filing": "single"},
                     {"min": 533401, "max": None,    "rate": 0.20, "filing": "single"},
                 ],
                 "niit": {"rate": 0.038, "threshold_single": 200000, "threshold_mfj": 250000, "label": "Net Investment Income Tax"},
             },
             "key_deductions": {
                 "SALT": {"limit": 10000, "items": ["State income tax", "Property tax", "Sales tax (if elected)"]},
                 "mortgage_interest": {"limit": 750000, "note": "Interest on first $750K of mortgage debt"},
                 "charitable": {"limit_pct": 0.60, "note": "Up to 60% of AGI for cash donations"},
                 "medical": {"threshold_pct": 0.075, "note": "Only amounts exceeding 7.5% of AGI"},
                 "student_loan_interest": {"limit": 2500, "phase_out_single": [80000, 95000]},
                 "educator_expense": {"limit": 300},
                 "home_office": {"method": "simplified", "rate_per_sqft": 5, "max_sqft": 300, "note": "Or actual expense method"},
                 "retirement_401k": {"limit": 23500, "catch_up_50plus": 7500},
                 "ira_traditional": {"limit": 7000, "catch_up_50plus": 1000},
                 "hsa": {"single": 4300, "family": 8550, "catch_up_55plus": 1000},
                 "qbi_199a": {"rate": 0.20, "note": "20% of Qualified Business Income for pass-through entities"},
             },
             "estimated_tax_schedule": [
                 {"due_date": "April 15", "payment": "Q1 — 25% of estimated annual tax"},
                 {"due_date": "June 15", "payment": "Q2 — 25% of estimated annual tax"},
                 {"due_date": "September 15", "payment": "Q3 — 25% of estimated annual tax"},
                 {"due_date": "January 15 (next year)", "payment": "Q4 — 25% of estimated annual tax"},
             ],
             "filing_deadlines": {
                 "individual_1040": "April 15",
                 "extension_4868": "October 15",
                 "corporate_1120": "April 15",
                 "partnership_1065": "March 15",
                 "s_corp_1120s": "March 15",
             },
             "penalties": {
                 "underpayment": "IRC §6654 — generally 8% annual rate on quarterly shortfall",
                 "late_filing": "5% of unpaid tax per month, max 25%",
                 "late_payment": "0.5% of unpaid tax per month, max 25%",
                 "safe_harbor": "Pay 100% of prior year tax (110% if AGI > $150K)",
             },
             "fica": {
                 "social_security_employee": 0.062,
                 "social_security_employer": 0.062,
                 "social_security_wage_base": 176100,
                 "medicare_employee": 0.0145,
                 "medicare_employer": 0.0145,
                 "additional_medicare": 0.009,
             },
         }},
    ]
    for jd in _default_jurisdictions:
        db.add(TaxJurisdiction(workspace_id=ws_id, **jd))

    # Default tax categories (common expense deduction mappings)
    _default_categories = [
        {"category": "Software & SaaS", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Office Supplies", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Professional Services", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Travel", "tax_code": TaxDeductibility.partially_deductible, "deduction_rate": Decimal("50"), "jurisdiction": "IN"},
        {"category": "Meals & Entertainment", "tax_code": TaxDeductibility.partially_deductible, "deduction_rate": Decimal("50"), "jurisdiction": "IN"},
        {"category": "Rent", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Utilities", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Insurance", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Marketing", "tax_code": TaxDeductibility.deductible, "deduction_rate": Decimal("100"), "jurisdiction": "IN"},
        {"category": "Personal", "tax_code": TaxDeductibility.non_deductible, "deduction_rate": Decimal("0"), "jurisdiction": "IN"},
    ]
    for cd in _default_categories:
        db.add(TaxCategory(workspace_id=ws_id, **cd))

    await db.flush()
    logger.info("Seeded default tax data for workspace %s", ws_id)


async def list_jurisdictions(db: AsyncSession, ws_id: uuid.UUID) -> list[TaxJurisdiction]:
    return list((await db.execute(select(TaxJurisdiction).where(TaxJurisdiction.workspace_id == ws_id).order_by(TaxJurisdiction.code))).scalars())

async def create_jurisdiction(db: AsyncSession, ws_id: uuid.UUID, data) -> TaxJurisdiction:
    jur = TaxJurisdiction(workspace_id=ws_id, name=data.name, code=data.code,
                           tax_rates_json=data.tax_rates_json, filing_frequency=data.filing_frequency)
    db.add(jur); await db.flush(); await db.refresh(jur); return jur

async def generate_tax_report(db: AsyncSession, ws_id: uuid.UUID, period_start: str, period_end: str, jurisdiction: str = "IN"):
    start = datetime.strptime(period_start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(period_end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    total_income = float((await db.execute(select(func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.income,
        Transaction.date >= start, Transaction.date < end)))).scalar() or 0)
    total_expenses = float((await db.execute(select(func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.expense,
        Transaction.date >= start, Transaction.date < end)))).scalar() or 0)
    tax_cats = await list_tax_categories(db, ws_id, jurisdiction)
    cat_map = {tc.category: tc for tc in tax_cats}
    cat_q = await db.execute(select(Transaction.category, func.sum(Transaction.amount)).where(and_(
        Transaction.workspace_id == ws_id, Transaction.type == TransactionType.expense,
        Transaction.date >= start, Transaction.date < end)).group_by(Transaction.category))
    categories, ded_total = [], 0.0
    for row in cat_q:
        cn, amt = row[0] or "Uncategorized", float(row[1] or 0)
        tc = cat_map.get(cn); dr = float(tc.deduction_rate) / 100 if tc else 0
        ded = amt * dr; ded_total += ded
        categories.append({"category": cn, "amount": round(amt, 2), "deduction_rate": dr,
                           "deductible_amount": round(ded, 2), "tax_code": tc.tax_code if tc else "non_deductible"})
    taxable = max(total_income - ded_total, 0)
    est_tax = float(_compute_slab_tax(Decimal(str(taxable)), jurisdiction))
    from schemas import TaxReportResponse
    return TaxReportResponse(period_start=period_start, period_end=period_end, jurisdiction=jurisdiction,
        total_income=round(total_income, 2), total_expenses=round(total_expenses, 2),
        deductible_expenses=round(ded_total, 2), taxable_income=round(taxable, 2),
        estimated_tax=round(est_tax, 2), effective_rate=round(est_tax / taxable if taxable > 0 else 0, 4),
        categories=categories)
