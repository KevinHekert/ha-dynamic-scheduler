import json
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

        body = await resp.text()
        records = _parse_easyenergy_body(
            body=body,
            window_start=now,
            window_end=window_end,
        )

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


def _parse_easyenergy_body(
    body: str,
    window_start: datetime,
    window_end: datetime,
) -> List[PriceRecord]:
    """Detecteer of de response JSON of XML is en parse naar PriceRecords."""

    text = body.lstrip("\ufeff \t\r\n")  # strip BOM + leading whitespace

    if text.startswith("[") or text.startswith("{"):
        # JSON-vorm, zoals in je logvoorbeeld
        return _parse_easyenergy_json(
            text,
            window_start=window_start,
            window_end=window_end,
        )

    # Fallback: XML-formaat parsen
    return _parse_easyenergy_xml(
        text,
        window_start=window_start,
        window_end=window_end,
    )


def _parse_easyenergy_json(
    json_text: str,
    window_start: datetime,
    window_end: datetime,
) -> List[PriceRecord]:
    """Parse de JSON-array met TariffUsage/TariffReturn naar PriceRecords."""

    try:
        data = json.loads(json_text)
    except Exception as err:
        _LOGGER.error(
            "EasyEnergy APX: JSON parse error: %s; body starts with: %.200s",
            err,
            json_text.replace("\n", " ")[:200],
        )
        return []

    if not isinstance(data, list):
        _LOGGER.warning(
            "EasyEnergy APX: unexpected JSON root type %s, expected list",
            type(data),
        )
        return []

    records: List[PriceRecord] = []

    window_start_local = dt_util.as_local(window_start)
    window_end_local = dt_util.as_local(window_end)

    for item in data:
        try:
            ts = item.get("Timestamp")
            if not ts:
                continue

            ts_dt = dt_util.parse_datetime(ts)
            if ts_dt is None:
                ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            slot_start_local = dt_util.as_local(ts_dt)
            slot_end_local = slot_start_local + timedelta(hours=1)

            # Alleen slots die overlappen met [window_start_local, window_end_local)
            if slot_end_local <= window_start_local or slot_start_local >= window_end_local:
                continue

            price_usage = float(item.get("TariffUsage"))

            records.append(
                PriceRecord(
                    start=slot_start_local,
                    end=slot_end_local,
                    value=price_usage,
                )
            )
        except Exception as err:
            _LOGGER.debug(
                "EasyEnergy APX: skipping JSON item %s due to error: %s", item, err
            )

    return records


def _parse_easyenergy_xml(
    xml_text: str,
    window_start: datetime,
    window_end: datetime,
) -> List[PriceRecord]:
    """Parset het ArrayOfEnergyTariff XML-formaat naar PriceRecords (fallback)."""

    ns = {
        "t": "http://schemas.datacontract.org/2004/07/GreatValue.Common.Models.Tariffs",
        "s": "http://schemas.datacontract.org/2004/07/System",
    }

    xml_clean = xml_text.lstrip("\ufeff \t\r\n")

    try:
        root = ET.fromstring(xml_clean)
    except ET.ParseError as err:
        _LOGGER.error(
            "EasyEnergy APX: XML parse error: %s; body starts with: %.200s",
            err,
            xml_text.replace("\n", " ")[:200],
        )
        return []

    records: List[PriceRecord] = []

    window_start_local = dt_util.as_local(window_start)
    window_end_local = dt_util.as_local(window_end)

    for tariff in root.findall("t:EnergyTariff", ns):
        try:
            usage_node = tariff.find("t:TariffUsage", ns)
            if usage_node is None or usage_node.text is None:
                continue
            price_usage = float(usage_node.text)

            dt_node = tariff.find("t:Timestamp/s:DateTime", ns)
            if dt_node is None or dt_node.text is None:
                continue

            dt_str = dt_node.text  # bijv. "2025-11-29T18:00:00Z"
            ts_dt = dt_util.parse_datetime(dt_str)
            if ts_dt is None:
                ts_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            slot_start_local = dt_util.as_local(ts_dt)
            slot_end_local = slot_start_local + timedelta(hours=1)

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
                "EasyEnergy APX: skipping XML tariff element due to error: %s", err
            )

    return records
