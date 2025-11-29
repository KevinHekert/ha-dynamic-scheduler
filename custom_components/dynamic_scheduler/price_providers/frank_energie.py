import logging
from datetime import datetime, timedelta, date
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from python_frank_energie import FrankEnergie
from python_frank_energie.models import MarketPrices, PriceData
from . import PriceProvider, PriceRecord

_LOGGER = logging.getLogger(__name__)


class FrankEnergyProvider(PriceProvider):
    """PriceProvider-implementatie voor Frank Energie."""

    def __init__(self, use_all_in: bool = True) -> None:
        # True = all-in tarief, False = kale marktprijs (nu nog niet gebruikt)
        self._use_all_in = use_all_in

    async def async_get_prices(
        self,
        hass: HomeAssistant,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        """Negeer voorlopig het venster en geef alle beschikbare slots terug."""
        return await async_get_prices(
            hass=hass,
            window_start=now,
            window_end=window_end,
            use_all_in=self._use_all_in,
        )


async def _fetch_prices_window(hass: HomeAssistant) -> PriceData:
    """Vraag elektriciteitsprijzen op voor vandaag + morgen (Frank Energie public prices)."""

    session = async_get_clientsession(hass)

    # anonieme client, public prices
    api = FrankEnergie(clientsession=session)

    # Officiële integratie gebruikt UTC-datums
    today: date = datetime.utcnow().date()
    tomorrow: date = today + timedelta(days=1)
    day_after: date = today + timedelta(days=2)

    prices_today: MarketPrices = await api.prices(today, tomorrow)
    prices_tomorrow: MarketPrices = await api.prices(tomorrow, day_after)

    # Combineer de twee PriceData-objecten (PriceData ondersteunt optellen)
    price_data: PriceData = prices_today.electricity + prices_tomorrow.electricity

    count_all = len(price_data.all)
    first_start = price_data.all[0].date_from if count_all else None
    last_start = price_data.all[-1].date_from if count_all else None

    _LOGGER.warning(
        (
            "Frank Energie provider: basisdataset bevat %d elektriciteit-slots "
            "(today+tomorrow), eerste=%s, laatste=%s"
        ),
        count_all,
        first_start,
        last_start,
    )

    return price_data


async def async_get_prices(
    hass: HomeAssistant,
    window_start: datetime,
    window_end: datetime,
    use_all_in: bool = True,
) -> List[PriceRecord]:
    """Geef ALLE PriceRecords terug die Frank nu heeft (zonder vensterfilter)."""

    price_data = await _fetch_prices_window(hass)

    records: List[PriceRecord] = []

    for item in price_data.all:
        # python-frank-energie PriceItem heeft o.a. date_from en total
        slot_start_raw: datetime = item.date_from

        # Converteer naar locale tijdzone (Europe/Amsterdam)
        slot_start = dt_util.as_local(slot_start_raw)
        slot_end = slot_start + timedelta(hours=1)

        price = float(item.total)
        records.append(PriceRecord(start=slot_start, end=slot_end, value=price))

    _LOGGER.warning(
        "Frank Energie provider: %d slots teruggegeven aan Dynamic Scheduler",
        len(records),
    )

    if records:
        _LOGGER.debug(
            "Eerste slot: %s–%s = %s, laatste slot: %s–%s = %s",
            records[0].start,
            records[0].end,
            records[0].value,
            records[-1].start,
            records[-1].end,
            records[-1].value,
        )

    return records
