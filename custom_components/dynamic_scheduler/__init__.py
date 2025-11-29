"""Dynamic Scheduler integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.CALENDAR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dynamic Scheduler integration (no YAML config)."""

    async def handle_schedule(call: ServiceCall) -> None:
        """Placeholder handler for the schedule service."""
        hass.logger.info(
            "Dynamic Scheduler: placeholder 'schedule' service called with data: %s",
            call.data,
        )

    hass.services.async_register(DOMAIN, "schedule", handle_schedule)

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
