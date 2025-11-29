"""Calendar platform for Dynamic Scheduler."""

from __future__ import annotations

from datetime import datetime
from typing import List

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Legacy setup (not used, but kept for completeness)."""
    return


class DynamicSchedulerCalendar(CalendarEntity):
    """Placeholder calendar entity for Dynamic Scheduler."""

    _attr_name = "Dynamic Scheduler"
    _attr_unique_id = "dynamic_scheduler_calendar"

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return no events yet (placeholder)."""
        return []
