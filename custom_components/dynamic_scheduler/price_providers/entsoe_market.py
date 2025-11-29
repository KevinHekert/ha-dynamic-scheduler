import logging
from datetime import datetime, timedelta
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import PriceProvider, PriceRecord

_LOGGER = logging.getLogger(__name__)


class EntsoeMarketProvider(PriceProvider):
    """PriceProvider voor ENTSO-E day-ahead marktprijzen."""

    def __init__(self, api_key: str, country_code: str = "NL") -> None:
        self._api_key = api_key
        self._country_code = country_code or "NL"

    async def async_get_prices(
        self,
        hass: HomeAssistant,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        """Run de (blokkerende) ENTSO-E call in een executor-thread."""
        return await hass.async_add_executor_job(
            _fetch_entsoe_prices,
            self._api_key,
            self._country_code,
        )


def _fetch_entsoe_prices(api_key: str, country_code: str) -> List[PriceRecord]:
    """Synchronous helper om ENTSO-E day-ahead prices op te halen."""

    from entsoe import EntsoePandasClient  # type: ignore
    import pandas as pd  # type: ignore

    client = EntsoePandasClient(api_key=api_key)

    # Haal vandaag + morgen op, in lokale tijdzone
    tz = dt_util.get_time_zone("Europe/Amsterdam")
    now_local = dt_util.now(tz)
    today_local = now_local.date()

    start = pd.Timestamp(today_local, tz=tz)
    end = start + pd.Timedelta(days=2)

    series = client.query_day_ahead_prices(country_code, start=start, end=end)

    records: List[PriceRecord] = []

    for ts, price_mwh in series.items():
        # ts is een pandas.Timestamp met tijdzone
        ts_dt = ts.to_pydatetime()
        slot_start = dt_util.as_local(ts_dt)
        slot_end = slot_start + timedelta(hours=1)

        # ENTSO-E prijzen zijn EUR/MWh -> omzetten naar EUR/kWh
        price_kwh = float(price_mwh) / 1000.0

        records.append(
            PriceRecord(
                start=slot_start,
                end=slot_end,
                value=price_kwh,
            )
        )

    _LOGGER.warning(
        "ENTSO-E provider: %d slots teruggegeven (country=%s)",
        len(records),
        country_code,
    )

    if records:
        _LOGGER.debug(
            "ENTSO-E provider: eerste slot %s–%s = %s, laatste slot %s–%s = %s",
            records[0].start,
            records[0].end,
            records[0].value,
            records[-1].start,
            records[-1].end,
            records[-1].value,
        )

    return records
