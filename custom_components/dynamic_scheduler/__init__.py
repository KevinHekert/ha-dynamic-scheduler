"""Dynamic Scheduler integration for Home Assistant."""

from __future__ import annotations
import logging
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .scheduler import store_test_slots_for_calendar


_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.CALENDAR]
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("calendar_entity_id"): cv.entity_id,
        vol.Required("deadline_time"): cv.time,  # wordt datetime.time
        vol.Required("runtime"): cv.time,        # wordt datetime.time
        vol.Optional("slot_length_minutes", default=60): vol.All(
            int, vol.Range(min=5, max=240)
        ),
        vol.Optional("continuous", default=False): cv.boolean,
        vol.Optional("clear_existing", default=True): cv.boolean,
    }
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dynamic Scheduler integration (no YAML config)."""

    async def handle_schedule(call: ServiceCall) -> None:
        """Basic schedule handler: parse calendar, runtime, and deadline."""
        calendar_entity_id: str = call.data["calendar_entity_id"]
        deadline_time = call.data["deadline_time"]   # type: time
        runtime_time = call.data["runtime"]          # type: time
        slot_length = call.data.get("slot_length_minutes", 60)
        continuous = call.data.get("continuous", False)
        clear_existing = call.data.get("clear_existing", True)

        # HA time-utils
        from homeassistant.util import dt as dt_util
        from datetime import timedelta

        now = dt_util.now()

        # Bereken eerstvolgende deadline
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

        # Voor nu alleen loggen zodat we weten dat alles goed binnenkomt
        _LOGGER.warning(
            "Dynamic Scheduler schedule(): calendar=%s deadline=%s runtime=%s (%s min) slot=%s continuous=%s clear=%s",
            calendar_entity_id,
            deadline,
            runtime_time,
            total_run_minutes,
            slot_length,
            continuous,
            clear_existing,
        )
        await store_test_slots_for_calendar(
            hass=hass,
            calendar_entity_id=calendar_entity_id,
            start=now,
            total_run_minutes=total_run_minutes,
            slot_length_minutes=slot_length,
            clear_existing=clear_existing,
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
