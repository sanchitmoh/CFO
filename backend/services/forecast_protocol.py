"""
AI CFO — Forecast Service Protocol (EXT-001)
Defines the interface for forecast implementations.

Swap implementations by changing the dependency in dependencies.py
without touching any router code.
"""
import uuid
from typing import Literal, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from schemas import ForecastResponse


@runtime_checkable
class ForecastService(Protocol):
    """Protocol defining the forecast service interface.

    Any class implementing this protocol can be injected via
    ``get_forecast_service`` in dependencies.py.

    Current implementations:
      - ``LinearForecastService`` (services/forecast_service.py) — linear regression
    """

    async def generate_forecast(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        months_ahead: int,
        scenario: Literal["optimistic", "base", "pessimistic"],
    ) -> ForecastResponse: ...
