"""Dynamic Scheduler integration for Home Assistant."""

from __future__ import annotations
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dynamic Scheduler integration (no config.yaml)."""
    async def handle_schedule(call: ServiceCall) -> None:
        """Placeholder handler for the schedule service."""
        hass.logger.info(
            "Dynamic Scheduler: placeholder 'schedule' service called with data: %s",
            call.data,
        )
    hass.services.async_register(DOMAIN, "schedule", handle_schedule)
    return True
