"""
AI CFO — Unit Tests for TaxCalculationService
Tests all 8 external tax API integrations with mocked httpx responses.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from services.tax_calculation_service import TaxCalculationService


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def svc():
    return TaxCalculationService()


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp,
        )
    return resp


# ── India Income Tax ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_india_tax_success(svc):
    mock_data = {
        "grossIncome": 1500000, "regime": "new-2026-27",
        "standardDeduction": 75000, "taxableIncome": 1425000,
        "incomeTax": 142500, "surcharge": 0, "cess": 5700,
        "totalTax": 148200, "effectiveRate": 0.0988,
        "rebate87A": 0, "brackets": [],
    }
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.calculate_india_tax(Decimal("1500000"), regime="new-2026-27")

        assert result["totalTax"] == 148200
        assert result["regime"] == "new-2026-27"
        client_instance.get.assert_called_once()
        call_args = client_instance.get.call_args
        assert "income-tax" in call_args[0][0]
        assert call_args[1]["params"]["grossIncome"] == 1500000.0


@pytest.mark.anyio
async def test_calculate_india_tax_api_failure(svc):
    mock_resp = _mock_response({}, status_code=500)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        with pytest.raises(ValueError, match="Tax calculation failed"):
            await svc.calculate_india_tax(Decimal("1500000"))


# ── India HRA ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_india_hra_success(svc):
    mock_data = {
        "basic": 600000, "hra": 240000, "rent": 240000,
        "metro": True, "exemptAmount": 120000, "taxableAmount": 120000,
    }
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.calculate_india_hra(
            Decimal("600000"), Decimal("240000"), Decimal("240000"), is_metro=True,
        )

        assert result["exemptAmount"] == 120000
        assert result["metro"] is True


@pytest.mark.anyio
async def test_calculate_india_hra_api_failure(svc):
    mock_resp = _mock_response({}, status_code=502)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        with pytest.raises(ValueError, match="HRA calculation failed"):
            await svc.calculate_india_hra(Decimal("600000"), Decimal("240000"), Decimal("240000"))


# ── India Gratuity ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_india_gratuity_success(svc):
    mock_data = {
        "basic": 50000, "years": 10, "covered": True,
        "gratuity": 230769, "taxFreeAmount": 230769,
        "taxableAmount": 0, "eligible": True,
    }
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.calculate_india_gratuity(Decimal("50000"), 10, covered_by_act=True)

        assert result["gratuity"] == 230769
        assert result["eligible"] is True


# ── US Self-Employment Tax ────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_us_tax_success(svc):
    mock_data = {
        "country": "us", "taxYear": 2025,
        "monthly": {"gross": 8333.33, "incomeTax": 1250, "socialInsurance": 1275, "net": 5808.33},
        "yearly": {"gross": 100000, "incomeTax": 15000, "socialInsurance": 15300, "totalDeductions": 30300, "net": 69700},
        "rates": {"effectiveTaxRate": 0.303, "dailyRate": 315.38, "hourlyRate": 39.42, "workingDays": 221},
    }
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.calculate_us_tax(Decimal("100000"), filing_status="single")

        assert result["yearly"]["net"] == 69700
        call_args = client_instance.get.call_args
        assert "calculate/us" in call_args[0][0]


# ── Multi-Country Tax ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_multi_country_tax_success(svc):
    mock_data = {
        "country": "de", "taxYear": 2025,
        "monthly": {"gross": 5000, "incomeTax": 900, "socialInsurance": 1050, "net": 3050},
        "yearly": {"gross": 60000, "incomeTax": 10800, "socialInsurance": 12600, "net": 36600},
        "rates": {"effectiveTaxRate": 0.39},
    }
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.calculate_multi_country_tax("de", Decimal("60000"), churchTax="9")

        assert result["country"] == "de"
        call_args = client_instance.get.call_args
        assert "calculate/de" in call_args[0][0]
        assert call_args[1]["params"]["churchTax"] == "9"


@pytest.mark.anyio
async def test_calculate_multi_country_tax_failure(svc):
    mock_resp = _mock_response({}, status_code=404)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        with pytest.raises(ValueError, match="tax calculation failed"):
            await svc.calculate_multi_country_tax("zz", Decimal("50000"))


# ── List Supported Countries ─────────────────────────────────────

@pytest.mark.anyio
async def test_list_supported_countries_success(svc):
    mock_data = [
        {"code": "in", "name": "India", "features": "income tax"},
        {"code": "us", "name": "United States", "features": "SE tax"},
        {"code": "de", "name": "Germany", "features": "church tax"},
    ]
    mock_resp = _mock_response(mock_data)

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_resp
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await svc.list_supported_countries()

        assert len(result) == 3
        assert result[0]["code"] == "in"


# ── Compare India Regimes ─────────────────────────────────────────

@pytest.mark.anyio
async def test_compare_india_regimes_new_is_better(svc):
    old_regime_data = {"totalTax": 200000, "regime": "old"}
    new_regime_data = {"totalTax": 148200, "regime": "new-2026-27"}

    call_count = 0
    async def mock_calc(gross_income, regime="new-2026-27", apply_standard_deduction=True):
        nonlocal call_count
        call_count += 1
        if regime == "old":
            return old_regime_data
        return new_regime_data

    svc.calculate_india_tax = mock_calc  # type: ignore
    result = await svc.compare_india_regimes(Decimal("1500000"))

    assert result["recommendation"] == "new_regime"
    assert result["savings"] == 200000 - 148200
    assert result["grossIncome"] == 1500000.0
    assert call_count == 2


@pytest.mark.anyio
async def test_compare_india_regimes_old_is_better(svc):
    old_regime_data = {"totalTax": 100000, "regime": "old"}
    new_regime_data = {"totalTax": 150000, "regime": "new-2026-27"}

    async def mock_calc(gross_income, regime="new-2026-27", apply_standard_deduction=True):
        if regime == "old":
            return old_regime_data
        return new_regime_data

    svc.calculate_india_tax = mock_calc  # type: ignore
    result = await svc.compare_india_regimes(Decimal("800000"))

    assert result["recommendation"] == "old_regime"
    assert result["savings"] < 0


# ── Effective Hourly Rate ─────────────────────────────────────────

@pytest.mark.anyio
async def test_calculate_effective_hourly_rate_success(svc):
    multi_country_data = {
        "country": "us",
        "yearly": {"gross": 100000, "net": 69700},
        "rates": {"hourlyRate": 39.42, "dailyRate": 315.38, "workingDays": 221, "effectiveTaxRate": 0.303},
    }

    async def mock_multi(country_code, income, **kwargs):
        return multi_country_data

    svc.calculate_multi_country_tax = mock_multi  # type: ignore
    result = await svc.calculate_effective_hourly_rate("us", Decimal("100000"), weekly_hours=40, paid_days_off=20)

    assert result["country"] == "us"
    assert result["grossIncome"] == 100000
    assert result["netIncome"] == 69700
    assert result["hourlyRate"] == 39.42
    assert result["workingDays"] == 221


# ── Timeout Handling ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_timeout_raises_value_error(svc):
    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.side_effect = httpx.ReadTimeout("Connection timed out")
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        with pytest.raises(ValueError, match="Tax calculation failed"):
            await svc.calculate_india_tax(Decimal("1500000"))


@pytest.mark.anyio
async def test_connection_error_raises_value_error(svc):
    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.side_effect = httpx.ConnectError("Connection refused")
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        with pytest.raises(ValueError, match="US tax calculation failed"):
            await svc.calculate_us_tax(Decimal("100000"))
