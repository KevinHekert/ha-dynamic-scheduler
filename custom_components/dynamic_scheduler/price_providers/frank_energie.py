"""Frank Energie price provider for Dynamic Scheduler (direct GraphQL API)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from . import PriceProvider, PriceRecord

FRANK_GRAPHQL_URL = "https://graphcdn.frankenergie.nl/"

class FrankEnergyProvider(PriceProvider):
    """Retrieves future electricity prices from Frank Energie GraphQL API."""

    def __init__(self, use_all_in: bool = True) -> None:
        """If use_all_in is True, use priceIncludingMarkup, else marketPrice."""
        self._use_all_in = use_all_in

    async def async_get_prices(
        self,
        hass: HomeAssistant,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        """Return PriceRecord list between now and window_end."""
        start_date = now.date().isoformat()
        end_date = window_end.date().isoformat()

        query = (
            "query MarketPrices($startDate: Date!, $endDate: Date!) {"
            "  marketPricesElectricity(startDate: $startDate, endDate: $endDate) {"
            "    from"
            "    till"
            "    marketPrice"
            "    priceIncludingMarkup"
            "  }"
            "}"
        )

        payload = {
            "query": query,
            "variables": {
                "startDate": start_date,
                "endDate": end_date,
            },
        }

        session = async_get_clientsession(hass)
        async with session.post(FRANK_GRAPHQL_URL, json=payload, timeout=20) as resp:
            resp.raise_for_status()
            data = await resp.json()

        items = data.get("data", {}).get("marketPricesElectricity") or []

        records: List[PriceRecord] = []
        for item in items:
            start = dt_util.parse_datetime(item["from"])
            end = dt_util.parse_datetime(item["till"])
            if start is None or end is None:
                continue

            # Filter op onze window
            if end <= now or start >= window_end:
                continue

            raw_value = (
                float(item["priceIncludingMarkup"])
                if self._use_all_in
                else float(item["marketPrice"])
            )

            records.append(PriceRecord(start=start, end=end, value=raw_value))

        records.sort(key=lambda r: r.start)
        return records
