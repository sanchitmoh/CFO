"""
AI CFO — External Tax Calculation API Integration
Free APIs: FinCalculator.in (India) + rel.tax (50 countries)
"""
import logging
from decimal import Decimal
from typing import Literal

import httpx

logger = logging.getLogger(__name__)


class TaxCalculationService:
    """
    External tax calculation API integration.
    
    Integrates with:
    - FinCalculator.in: Free India tax calculator
    - rel.tax: Free 50-country B2B tax calculator
    """
    
    FINCALC_BASE = "https://fincalculator.in/api/v1"
    RELTAX_BASE = "https://rel.tax/v1"
    TIMEOUT = 10.0  # seconds
    
    # ── India Tax Calculation (FinCalculator.in) ──────────────────────
    
    async def calculate_india_tax(
        self,
        gross_income: Decimal,
        regime: Literal["old", "new-2024-25", "new-2025-26", "new-2026-27"] = "new-2026-27",
        apply_standard_deduction: bool = True,
    ) -> dict:
        """
        Calculate India income tax using FinCalculator.in API.
        
        Args:
            gross_income: Annual gross income in ₹
            regime: Tax regime (old or new-2024-25/2025-26/2026-27)
            apply_standard_deduction: Apply standard deduction (default: True)
        
        Returns:
            {
                "grossIncome": 1500000,
                "regime": "new-2026-27",
                "standardDeduction": 75000,
                "taxableIncome": 1425000,
                "incomeTax": 142500,
                "surcharge": 0,
                "cess": 5700,
                "totalTax": 148200,
                "effectiveRate": 0.0988,
                "rebate87A": 0,
                "brackets": [...]
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.FINCALC_BASE}/income-tax",
                    params={
                        "grossIncome": float(gross_income),
                        "regime": regime,
                        "applyStandardDeduction": apply_standard_deduction,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"FinCalculator.in API error: {e}")
            raise ValueError(f"Tax calculation failed: {str(e)}")
    
    async def calculate_india_hra(
        self,
        basic_salary: Decimal,
        hra_received: Decimal,
        rent_paid: Decimal,
        is_metro: bool = True,
    ) -> dict:
        """
        Calculate HRA exemption under Section 10(13A).
        
        Args:
            basic_salary: Annual basic + DA in ₹
            hra_received: Annual HRA received in ₹
            rent_paid: Annual rent paid in ₹
            is_metro: Metro city (50% cap) or non-metro (40% cap)
        
        Returns:
            {
                "basic": 600000,
                "hra": 240000,
                "rent": 240000,
                "metro": true,
                "exemptAmount": 120000,
                "taxableAmount": 120000,
                "bounds": {
                    "actualHRA": 240000,
                    "rentMinus10Percent": 180000,
                    "metroPercent": 300000
                }
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.FINCALC_BASE}/hra",
                    params={
                        "basic": float(basic_salary),
                        "hra": float(hra_received),
                        "rent": float(rent_paid),
                        "metro": is_metro,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"FinCalculator.in HRA API error: {e}")
            raise ValueError(f"HRA calculation failed: {str(e)}")
    
    async def calculate_india_gratuity(
        self,
        monthly_basic: Decimal,
        years_of_service: int,
        covered_by_act: bool = True,
    ) -> dict:
        """
        Calculate gratuity under Payment of Gratuity Act, 1972.
        
        Args:
            monthly_basic: Last drawn monthly basic + DA in ₹
            years_of_service: Years of continuous service
            covered_by_act: Employer has ≥10 employees (15/26 formula)
        
        Returns:
            {
                "basic": 50000,
                "years": 10,
                "covered": true,
                "gratuity": 230769,
                "taxFreeAmount": 230769,
                "taxableAmount": 0,
                "eligible": true
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.FINCALC_BASE}/gratuity",
                    params={
                        "basic": float(monthly_basic),
                        "years": years_of_service,
                        "covered": covered_by_act,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"FinCalculator.in Gratuity API error: {e}")
            raise ValueError(f"Gratuity calculation failed: {str(e)}")
    
    # ── US Tax Calculation (rel.tax) ──────────────────────────────────
    
    async def calculate_us_tax(
        self,
        income: Decimal,
        filing_status: Literal["single"] = "single",
        qbi_deduction: bool = True,
    ) -> dict:
        """
        Calculate US self-employment tax using rel.tax API.
        
        Args:
            income: Net self-employment income in USD
            filing_status: Filing status (currently only 'single' supported)
            qbi_deduction: Apply QBI deduction (20%)
        
        Returns:
            {
                "country": "us",
                "taxYear": 2025,
                "monthly": {
                    "gross": 8333.33,
                    "incomeTax": 1250.00,
                    "socialInsurance": 1275.00,
                    "net": 5808.33
                },
                "yearly": {
                    "gross": 100000,
                    "incomeTax": 15000,
                    "socialInsurance": 15300,
                    "totalDeductions": 30300,
                    "net": 69700
                },
                "rates": {
                    "effectiveTaxRate": 0.303,
                    "dailyRate": 315.38,
                    "hourlyRate": 39.42,
                    "workingDays": 221
                }
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.RELTAX_BASE}/calculate/us",
                    params={
                        "income": float(income),
                        "filingStatus": filing_status,
                        "qbiDeduction": qbi_deduction,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"rel.tax US API error: {e}")
            raise ValueError(f"US tax calculation failed: {str(e)}")
    
    # ── Multi-Country Tax Calculation (rel.tax) ───────────────────────
    
    async def calculate_multi_country_tax(
        self,
        country_code: str,
        income: Decimal,
        **kwargs,
    ) -> dict:
        """
        Calculate tax for any of 50 countries using rel.tax API.
        
        Supported countries:
        - IN (India), US (USA), GB (UK), CA (Canada), DE (Germany)
        - AU (Australia), SG (Singapore), AE (UAE), and 42 more
        
        Args:
            country_code: Two-letter ISO country code (e.g., 'in', 'us', 'gb')
            income: Annual gross income in local currency
            **kwargs: Country-specific parameters
        
        Returns:
            {
                "country": "de",
                "taxYear": 2025,
                "monthly": {...},
                "yearly": {...},
                "rates": {...},
                "details": {...}
            }
        
        Example:
            # Germany
            await calculate_multi_country_tax(
                "de", 
                Decimal("60000"), 
                churchTax="9", 
                hasChildren=True
            )
            
            # India (alternative to FinCalculator.in)
            await calculate_multi_country_tax(
                "in",
                Decimal("1500000"),
                taxModel="new_regime"
            )
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.RELTAX_BASE}/calculate/{country_code.lower()}",
                    params={"income": float(income), **kwargs},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"rel.tax {country_code.upper()} API error: {e}")
            raise ValueError(f"{country_code.upper()} tax calculation failed: {str(e)}")
    
    async def list_supported_countries(self) -> list[dict]:
        """
        List all 50 countries supported by rel.tax.
        
        Returns:
            [
                {"code": "in", "name": "India", "features": "..."},
                {"code": "us", "name": "United States", "features": "..."},
                ...
            ]
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(f"{self.RELTAX_BASE}/countries")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"rel.tax countries API error: {e}")
            raise ValueError(f"Failed to fetch countries: {str(e)}")
    
    async def get_country_info(self, country_code: str) -> dict:
        """
        Get detailed parameter documentation for a specific country.
        
        Args:
            country_code: Two-letter ISO country code
        
        Returns:
            {
                "code": "in",
                "name": "India",
                "taxYear": 2025,
                "parameters": [...],
                "examples": [...]
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.RELTAX_BASE}/countries/{country_code.lower()}"
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"rel.tax country info API error: {e}")
            raise ValueError(f"Failed to fetch country info: {str(e)}")
    
    # ── Tax Comparison & Optimization ─────────────────────────────────
    
    async def compare_india_regimes(
        self,
        gross_income: Decimal,
    ) -> dict:
        """
        Compare old vs new tax regime for India.
        
        Args:
            gross_income: Annual gross income in ₹
        
        Returns:
            {
                "grossIncome": 1500000,
                "oldRegime": {...},
                "newRegime": {...},
                "savings": 25000,
                "recommendation": "new_regime"
            }
        """
        old_regime = await self.calculate_india_tax(gross_income, regime="old")
        new_regime = await self.calculate_india_tax(gross_income, regime="new-2026-27")
        
        old_tax = old_regime.get("totalTax", 0)
        new_tax = new_regime.get("totalTax", 0)
        savings = old_tax - new_tax
        
        return {
            "grossIncome": float(gross_income),
            "oldRegime": old_regime,
            "newRegime": new_regime,
            "savings": savings,
            "recommendation": "new_regime" if savings > 0 else "old_regime",
        }
    
    async def calculate_effective_hourly_rate(
        self,
        country_code: str,
        annual_income: Decimal,
        weekly_hours: int = 40,
        paid_days_off: int = 20,
    ) -> dict:
        """
        Calculate effective hourly rate after all taxes and deductions.
        
        Args:
            country_code: Two-letter ISO country code
            annual_income: Annual gross income in local currency
            weekly_hours: Weekly working hours (default: 40)
            paid_days_off: Annual paid days off (default: 20)
        
        Returns:
            {
                "country": "us",
                "grossIncome": 100000,
                "netIncome": 69700,
                "hourlyRate": 39.42,
                "dailyRate": 315.38,
                "workingDays": 221,
                "effectiveTaxRate": 0.303
            }
        """
        result = await self.calculate_multi_country_tax(
            country_code,
            annual_income,
            weeklyHours=weekly_hours,
            paidDaysOff=paid_days_off,
        )
        
        return {
            "country": result["country"],
            "grossIncome": result["yearly"]["gross"],
            "netIncome": result["yearly"]["net"],
            "hourlyRate": result["rates"]["hourlyRate"],
            "dailyRate": result["rates"]["dailyRate"],
            "workingDays": result["rates"]["workingDays"],
            "effectiveTaxRate": result["rates"]["effectiveTaxRate"],
        }
