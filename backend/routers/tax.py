"""
AI CFO — Tax Management Router
Tax categories, quarterly estimates, jurisdictions, reports,
and external tax calculation API integration.
"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User
from schemas import (
    TaxCategoryCreate, TaxCategoryOut, TaxEstimateCreate, TaxEstimateUpdate, TaxEstimateOut,
    TaxJurisdictionCreate, TaxJurisdictionOut, TaxReportResponse,
    # External tax calculation schemas
    IndiaTaxCalculationRequest, IndiaHRACalculationRequest, IndiaGratuityCalculationRequest,
    USTaxCalculationRequest, MultiCountryTaxRequest,
    IndiaRegimeComparisonRequest, EffectiveHourlyRateRequest,
    ExternalTaxCalculationResponse, IndiaRegimeComparisonResponse, EffectiveHourlyRateResponse,
)
from services import tax_service
from services.tax_calculation_service import TaxCalculationService
from services.audit_service import log_action

router = APIRouter()

# Singleton external tax calculation service
_calc_service = TaxCalculationService()


# ── Tax Categories ─────────────────────────────────────────────────

@router.get("/categories", response_model=list[TaxCategoryOut])
async def list_categories(
    jurisdiction: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    cats = await tax_service.list_tax_categories(db, user.workspace_id, jurisdiction)
    return [TaxCategoryOut.model_validate(c) for c in cats]


@router.post("/categories", response_model=TaxCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: TaxCategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    cat = await tax_service.create_tax_category(db, user.workspace_id, data)
    await db.commit()
    await log_action(db, user, "tax.category.create", "tax_category", cat.id, new_value={"category": data.category})
    return TaxCategoryOut.model_validate(cat)


# ── Tax Estimates ──────────────────────────────────────────────────

@router.get("/available-quarters")
async def available_quarters(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Return quarters that have transaction data, newest first."""
    from sqlalchemy import select, func, extract, literal_column
    from models import Transaction
    
    # Define the year and quarter expressions
    year_expr = extract("year", Transaction.date)
    quarter_expr = func.ceil(extract("month", Transaction.date) / 3.0)
    
    rows = (await db.execute(
        select(
            year_expr.label("y"),
            quarter_expr.label("q"),
        )
        .where(Transaction.workspace_id == user.workspace_id)
        .group_by(year_expr, quarter_expr)
        .order_by(year_expr.desc(), quarter_expr.desc())
    )).all()
    return [f"{int(r[0])}-Q{int(r[1])}" for r in rows]

@router.get("/estimates", response_model=list[TaxEstimateOut])
async def list_estimates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    estimates = await tax_service.list_tax_estimates(db, user.workspace_id)
    return [TaxEstimateOut.model_validate(e) for e in estimates]


@router.post("/estimates", response_model=TaxEstimateOut, status_code=status.HTTP_201_CREATED)
async def compute_estimate(
    data: TaxEstimateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    estimate = await tax_service.compute_quarterly_estimate(db, user.workspace_id, data)
    await db.commit()
    return TaxEstimateOut.model_validate(estimate)


# ── Tax Jurisdictions ──────────────────────────────────────────────

@router.get("/jurisdictions", response_model=list[TaxJurisdictionOut])
async def list_jurisdictions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    jurs = await tax_service.list_jurisdictions(db, user.workspace_id)
    # Auto-seed default data for existing workspaces that predate the seed
    if not jurs:
        try:
            await tax_service.seed_default_tax_data(db, user.workspace_id)
            await db.commit()
            jurs = await tax_service.list_jurisdictions(db, user.workspace_id)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Auto-seed failed for workspace %s", user.workspace_id, exc_info=True)
    return [TaxJurisdictionOut.model_validate(j) for j in jurs]


@router.post("/jurisdictions", response_model=TaxJurisdictionOut, status_code=status.HTTP_201_CREATED)
async def create_jurisdiction(
    data: TaxJurisdictionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    jur = await tax_service.create_jurisdiction(db, user.workspace_id, data)
    await db.commit()
    return TaxJurisdictionOut.model_validate(jur)


# ── Tax Report ─────────────────────────────────────────────────────

@router.get("/report", response_model=TaxReportResponse)
async def tax_report(
    period_start: str = Query(..., description="YYYY-MM-DD"),
    period_end: str = Query(..., description="YYYY-MM-DD"),
    jurisdiction: str = Query("IN"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await tax_service.generate_tax_report(db, user.workspace_id, period_start, period_end, jurisdiction)


# ═══════════════════════════════════════════════════════════════════
# EXTERNAL TAX CALCULATION APIs (FinCalculator.in + rel.tax)
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/calculate/india",
    response_model=ExternalTaxCalculationResponse,
    summary="India income tax (FinCalculator.in)",
)
async def calculate_india_tax(
    data: IndiaTaxCalculationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate India income tax using the free FinCalculator.in API.
    Supports old and new regime (2024-27), standard deduction, 87A rebate,
    surcharge, and 4% health & education cess."""
    try:
        result = await _calc_service.calculate_india_tax(
            gross_income=Decimal(str(data.gross_income)),
            regime=data.regime,
            apply_standard_deduction=data.apply_standard_deduction,
        )
        await log_action(db, user, "tax.calculate.india", "tax_calculation", None,
                         new_value={"regime": data.regime, "gross_income": data.gross_income})
        return ExternalTaxCalculationResponse(source="fincalculator.in", country="IN", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/india/hra",
    response_model=ExternalTaxCalculationResponse,
    summary="India HRA exemption (FinCalculator.in)",
)
async def calculate_india_hra(
    data: IndiaHRACalculationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate HRA exemption under Section 10(13A) using FinCalculator.in."""
    try:
        result = await _calc_service.calculate_india_hra(
            basic_salary=Decimal(str(data.basic_salary)),
            hra_received=Decimal(str(data.hra_received)),
            rent_paid=Decimal(str(data.rent_paid)),
            is_metro=data.is_metro,
        )
        await log_action(db, user, "tax.calculate.india.hra", "tax_calculation", None,
                         new_value={"is_metro": data.is_metro})
        return ExternalTaxCalculationResponse(source="fincalculator.in", country="IN", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/india/gratuity",
    response_model=ExternalTaxCalculationResponse,
    summary="India gratuity (FinCalculator.in)",
)
async def calculate_india_gratuity(
    data: IndiaGratuityCalculationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate gratuity under Payment of Gratuity Act, 1972."""
    try:
        result = await _calc_service.calculate_india_gratuity(
            monthly_basic=Decimal(str(data.monthly_basic)),
            years_of_service=data.years_of_service,
            covered_by_act=data.covered_by_act,
        )
        await log_action(db, user, "tax.calculate.india.gratuity", "tax_calculation", None,
                         new_value={"years": data.years_of_service})
        return ExternalTaxCalculationResponse(source="fincalculator.in", country="IN", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/us",
    response_model=ExternalTaxCalculationResponse,
    summary="US self-employment tax (rel.tax)",
)
async def calculate_us_tax(
    data: USTaxCalculationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate US self-employment tax using the free rel.tax API.
    Includes federal income tax, Social Security, Medicare, and optional QBI deduction."""
    try:
        result = await _calc_service.calculate_us_tax(
            income=Decimal(str(data.income)),
            filing_status=data.filing_status,
            qbi_deduction=data.qbi_deduction,
        )
        await log_action(db, user, "tax.calculate.us", "tax_calculation", None,
                         new_value={"filing_status": data.filing_status})
        return ExternalTaxCalculationResponse(source="rel.tax", country="US", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/global",
    response_model=ExternalTaxCalculationResponse,
    summary="Multi-country tax (rel.tax, 50 countries)",
)
async def calculate_multi_country_tax(
    data: MultiCountryTaxRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate tax for any of 50 countries using the free rel.tax API.
    Pass country-specific parameters via `extra_params`."""
    try:
        kwargs = data.extra_params or {}
        result = await _calc_service.calculate_multi_country_tax(
            country_code=data.country_code,
            income=Decimal(str(data.income)),
            **kwargs,
        )
        await log_action(db, user, "tax.calculate.global", "tax_calculation", None,
                         new_value={"country": data.country_code})
        return ExternalTaxCalculationResponse(
            source="rel.tax", country=data.country_code.upper(), data=result,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get(
    "/calculate/countries",
    summary="List supported countries (rel.tax)",
)
async def list_supported_countries(
    user: User = Depends(get_current_user),
):
    """Return all 50 countries supported by the rel.tax tax calculator."""
    try:
        return await _calc_service.list_supported_countries()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/india/compare-regimes",
    response_model=IndiaRegimeComparisonResponse,
    summary="Compare India old vs new regime",
)
async def compare_india_regimes(
    data: IndiaRegimeComparisonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Compare old vs new tax regime for India and recommend the optimal one."""
    try:
        result = await _calc_service.compare_india_regimes(
            gross_income=Decimal(str(data.gross_income)),
        )
        await log_action(db, user, "tax.calculate.india.compare", "tax_calculation", None,
                         new_value={"gross_income": data.gross_income, "recommendation": result["recommendation"]})
        return IndiaRegimeComparisonResponse(
            gross_income=result["grossIncome"],
            old_regime=result["oldRegime"],
            new_regime=result["newRegime"],
            savings=result["savings"],
            recommendation=result["recommendation"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post(
    "/calculate/hourly-rate",
    response_model=EffectiveHourlyRateResponse,
    summary="Effective post-tax hourly rate",
)
async def calculate_effective_hourly_rate(
    data: EffectiveHourlyRateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Calculate the effective hourly rate after all taxes and deductions for any country."""
    try:
        result = await _calc_service.calculate_effective_hourly_rate(
            country_code=data.country_code,
            annual_income=Decimal(str(data.annual_income)),
            weekly_hours=data.weekly_hours,
            paid_days_off=data.paid_days_off,
        )
        await log_action(db, user, "tax.calculate.hourly_rate", "tax_calculation", None,
                         new_value={"country": data.country_code})
        return EffectiveHourlyRateResponse(
            country=result["country"],
            gross_income=result["grossIncome"],
            net_income=result["netIncome"],
            hourly_rate=result["hourlyRate"],
            daily_rate=result["dailyRate"],
            working_days=result["workingDays"],
            effective_tax_rate=result["effectiveTaxRate"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

