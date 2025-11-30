"""Dynamic Scheduler integration for Home Assistant."""

from __future__ import annotations
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util, slugify

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_PROVIDER_CONFIG,
    CONF_TARIFF_RESOLUTION,
    TARIFF_RESOLUTION_HOURLY,
    TARIFF_RESOLUTION_QUARTER_HOURLY,
)
from .price_providers import create_price_provider
from .scheduler import schedule_calendar_from_prices

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.CALENDAR]

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("calendar_entity_id"): cv.entity_id,
        vol.Required("deadline_time"): cv.time,  # wordt datetime.time
        vol.Required("runtime"): cv.time,        # wordt datetime.time
        # Geen default meer hier, zodat we kunnen zien of de gebruiker 'm echt meegeeft
        vol.Optional("slot_length_minutes"): vol.All(
            int, vol.Range(min=5, max=240)
        ),
        vol.Optional("continuous", default=False): cv.boolean,
        vol.Optional("clear_existing", default=True): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dynamic Scheduler integration (no YAML config)."""

    async def handle_schedule(call: ServiceCall) -> None:
        """Schedule handler: parse inputs, fetch prices, and write calendar events."""

        calendar_entity_id: str = call.data["calendar_entity_id"]
        deadline_time = call.data["deadline_time"]   # datetime.time
        runtime_time = call.data["runtime"]          # datetime.time
        slot_length_override = call.data.get("slot_length_minutes")
        continuous = call.data.get("continuous", False)
        clear_existing = call.data.get("clear_existing", True)

        now = dt_util.now()

        # 1) Eerstvolgende deadline bepalen
        deadline = now.replace(
            hour=deadline_time.hour,
            minute=deadline_time.minute,
            second=deadline_time.second,
            microsecond=0,
        )
        if deadline <= now:
            deadline += timedelta(days=1)

        # Runtime HH:MM -> minuten
        total_run_minutes = runtime_time.hour * 60 + runtime_time.minute

        # 2) Bijbehorende config entry zoeken (op basis van naam -> entity_id)
        #    entity_id = 'calendar.auto'  ->  'auto'
        cal_slug = (
            calendar_entity_id.split(".", 1)[1]
            if "." in calendar_entity_id
            else calendar_entity_id
        )

        target_entry: ConfigEntry | None = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            name = entry.data.get("name") or entry.title
            if name and slugify(name) == cal_slug:
                target_entry = entry
                break

        if target_entry is None:
            _LOGGER.error(
                "Dynamic Scheduler: no config entry found for calendar %s (slug=%s)",
                calendar_entity_id,
                cal_slug,
            )
            return

        # 3) Tarief-resolutie uit config entry (bepaalt standaard base_minutes)
        tariff_resolution = target_entry.data.get(
            CONF_TARIFF_RESOLUTION,
            TARIFF_RESOLUTION_HOURLY,
        )

        if tariff_resolution == TARIFF_RESOLUTION_QUARTER_HOURLY:
            default_base_minutes = 15
        else:
            default_base_minutes = 60

        # slot_length_override uit de service-call (indien meegegeven) gaat vóór
        base_minutes = slot_length_override or default_base_minutes

        _LOGGER.warning(
            (
                "Dynamic Scheduler schedule(): calendar=%s deadline=%s "
                "runtime=%s (%s min) base_minutes=%s "
                "tariff_resolution=%s continuous=%s clear=%s"
            ),
            calendar_entity_id,
            deadline,
            runtime_time,
            total_run_minutes,
            base_minutes,
            tariff_resolution,
            continuous,
            clear_existing,
        )

        # 4) Provider-object maken op basis van config entry
        provider_cfg = {
            CONF_PROVIDER: target_entry.data[CONF_PROVIDER],
            CONF_PROVIDER_CONFIG: target_entry.data.get(CONF_PROVIDER_CONFIG, {}),
        }
        provider = create_price_provider(provider_cfg)

        # 5) Prijzen ophalen bij provider
        price_records = await provider.async_get_prices(hass, now, deadline)

        _LOGGER.warning(
            "Dynamic Scheduler: fetched %d price records from provider for window %s -> %s",
            len(price_records),
            now,
            deadline,
        )
        if price_records:
            _LOGGER.warning(
                "Dynamic Scheduler: first record %s -> %s = %s",
                price_records[0].start,
                price_records[0].end,
                price_records[0].value,
            )

        # 6) Echte scheduler gebruiken
        await schedule_calendar_from_prices(
            hass=hass,
            calendar_entity_id=calendar_entity_id,
            price_records=price_records,
            window_start=now,
            window_end=deadline,
            total_run_minutes=total_run_minutes,
            continuous=continuous,
            clear_existing=clear_existing,
            base_minutes=base_minutes,
        )

    hass.services.async_register(
        DOMAIN,
        "schedule",
        handle_schedule,
        schema=SERVICE_SCHEMA,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Scheduler from a config entry."""
    # Zorg dat we een plek hebben voor runtime-data
    hass.data.setdefault(DOMAIN, {})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Dynamic Scheduler config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
