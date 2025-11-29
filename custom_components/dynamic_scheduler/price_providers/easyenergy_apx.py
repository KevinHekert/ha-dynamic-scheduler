import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from . import PriceProvider, PriceRecord

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://mijn.easyenergy.com/nl/api/tariff/getapxtariffs"


class EasyEnergyApxProvider(PriceProvider):
    """PriceProvider voor EasyEnergy APX day-ahead (inkoop) tarieven."""

    async def async_get_prices(
        self,
        hass: HomeAssistant,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        """Haal APX-tarieven op bij EasyEnergy en map naar PriceRecord."""

        session = async_get_clientsession(hass)

        # EasyEnergy verwacht UTC-tijden in ISO8601 met 'Z'
        utc_start = dt_util.as_utc(now)
        utc_end = dt_util.as_utc(window_end)

        def _fmt(dt: datetime) -> str:
            """Formateer als ISO8601 met 'Z' suffix (zoals in jouw voorbeeld)."""
            iso = dt.isoformat(timespec="seconds")
            if iso.endswith("+00:00"):
                iso = iso[:-6] + "Z"
            return iso

        params = {
            "startTimestamp": _fmt(utc_start),
            "endTimestamp": _fmt(utc_end),
            "grouping": "",
        }

        _LOGGER.debug(
            "EasyEnergy APX: requesting %s with params %s",
            BASE_URL,
            params,
        )

        try:
            resp = await session.get(BASE_URL, params=params, timeout=10)
        except Exception as err:
            _LOGGER.warning("EasyEnergy APX: request failed: %s", err)
            return []

        if resp.status != 200:
            text = await resp.text()
            _LOGGER.warning(
                "EasyEnergy APX: HTTP %s from API, body starts with: %.200s",
                resp.status,
                text.replace("\n", " ")[:200],
            )
            return []

        xml_text = await resp.text()
        records = _parse_easyenergy_xml(xml_text, window_start=now, window_end=window_end)

        _LOGGER.warning(
            "EasyEnergy APX provider: %d slots returned for window %s -> %s",
            len(records),
            now,
            window_end,
        )

        if records:
            _LOGGER.debug(
                "EasyEnergy APX provider: first %s–%s = %s, last %s–%s = %s",
                records[0].start,
                records[0].end,
                records[0].value,
                records[-1].start,
                records[-1].end,
                records[-1].value,
            )

        return records


def _parse_easyenergy_xml(
    xml_text: str,
    window_start: datetime,
    window_end: datetime,
) -> List[PriceRecord]:
    """Parset het ArrayOfEnergyTariff XML-formaat naar PriceRecords."""

    # Namespaces uit jouw voorbeeld
    ns = {
        "t": "http://schemas.datacontract.org/2004/07/GreatValue.Common.Models.Tariffs",
        "s": "http://schemas.datacontract.org/2004/07/System",
    }

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        _LOGGER.error("EasyEnergy APX: XML parse error: %s", err)
        return []

    records: List[PriceRecord] = []

    # Vergelijking in lokale tijd
    window_start_local = dt_util.as_local(window_start)
    window_end_local = dt_util.as_local(window_end)

    for tariff in root.findall("t:EnergyTariff", ns):
        try:
            # <TariffUsage>...</TariffUsage>
            usage_node = tariff.find("t:TariffUsage", ns)
            if usage_node is None or usage_node.text is None:
                continue
            price_usage = float(usage_node.text)

            # <Timestamp><d3p1:DateTime>...</d3p1:DateTime></Timestamp>
            dt_node = tariff.find("t:Timestamp/s:DateTime", ns)
            if dt_node is None or dt_node.text is None:
                continue

            dt_str = dt_node.text  # bijv. "2025-11-29T18:00:00Z"
            ts_dt = dt_util.parse_datetime(dt_str)
            if ts_dt is None:
                # Fallback: fromisoformat met Z→+00:00
                ts_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            slot_start_local = dt_util.as_local(ts_dt)
            slot_end_local = slot_start_local + timedelta(hours=1)

            # Alleen slots die overlappen met [window_start_local, window_end_local)
            if slot_end_local <= window_start_local or slot_start_local >= window_end_local:
                continue

            records.append(
                PriceRecord(
                    start=slot_start_local,
                    end=slot_end_local,
                    value=price_usage,
                )
            )
        except Exception as err:
            _LOGGER.debug(
                "EasyEnergy APX: skipping tariff element due to error: %s", err
            )

    return records
