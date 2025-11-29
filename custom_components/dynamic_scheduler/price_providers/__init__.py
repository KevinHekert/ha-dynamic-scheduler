"""Price provider interface for Dynamic Scheduler."""

from __future__ import annotations

from typing import Protocol, List
from datetime import datetime


class PriceRecord:
    def __init__(self, start: datetime, end: datetime, value: float):
        self.start = start
        self.end = end
        self.value = value


class PriceProvider(Protocol):
    """Protocol for price providers."""

    async def async_get_prices(
        self,
        hass,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        ...
