from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Every config entry gives one calendar."""
    name = entry.title or "Dynamic Scheduler"
    entity_id = f"{DOMAIN}_{entry.entry_id}"

    calendar = DynamicSchedulerCalendar(
        hass=hass,
        entry_id=entry.entry_id,
        name=name,
        unique_id=entity_id,
    )
    async_add_entities([calendar])


class DynamicSchedulerCalendar(CalendarEntity):
    """Calendar filled by the Dynamic Scheduler service."""

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, unique_id: str):
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def events_data(self) -> List[Dict[str, Any]]:
        """Events stored by the integration."""
        domain = self.hass.data.setdefault(DOMAIN, {})
        return domain.setdefault("events_by_calendar", {}).get(self.entity_id, [])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events between start and end."""
        result = []
        for ev in self.events_data:
            if ev["end"] <= start_date or ev["start"] >= end_date:
                continue
            result.append(
                CalendarEvent(
                    summary=ev.get("summary", self.name),
                    start=ev["start"],
                    end=ev["end"],
                    description=ev.get("description"),
                )
            )
        return result
