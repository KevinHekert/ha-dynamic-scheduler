"""Dynamic Scheduler integration for Home Assistant."""

from homeassistant.core import HomeAssistant

DOMAIN = "dynamic_scheduler"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Dynamic Scheduler integration (no config.yaml)."""
    return True
