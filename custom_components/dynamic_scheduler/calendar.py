"""Calendar platform for the Dynamic Scheduler integration."""

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
    """Set up a Dynamic Scheduler calendar for this config entry."""

    name = entry.data.get("name", entry.title)
    unique_id = f"{entry.entry_id}"

    calendar = DynamicSchedulerCalendar(
        hass=hass,
        entry_id=entry.entry_id,
        name=name,
        unique_id=unique_id,
    )

    async_add_entities([calendar])


class DynamicSchedulerCalendar(CalendarEntity):
    """Calendar entity for a single Dynamic Scheduler entry."""

    _attr_should_poll = False  # we push zelf data, geen polling nodig

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, unique_id: str):
        self.hass = hass
        self._entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = unique_id

    # -------------------------
    # EVENT DATA PER CALENDAR
    # -------------------------
    @property
    def events_data(self) -> List[Dict[str, Any]]:
        """Return stored events for this calendar."""
        domain = self.hass.data.setdefault(DOMAIN, {})
        events = domain.setdefault("events_by_calendar", {})
        return events.setdefault(self._attr_unique_id, [])

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return events between start and end."""
        results: List[CalendarEvent] = []

        for ev in self.events_data:
            if ev["end"] <= start_date or ev["start"] >= end_date:
                continue

            results.append(
                CalendarEvent(
                    summary=ev.get("summary", self.name),
                    start=ev["start"],
                    end=ev["end"],
                    description=ev.get("description"),
                )
            )

        return results

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event (for calendar state)."""
        from homeassistant.util import dt as dt_util

        now = dt_util.utcnow()
        future = [ev for ev in self.events_data if ev["end"] > now]
        if not future:
            return None

        ev = sorted(future, key=lambda e: e["start"])[0]
        return CalendarEvent(
            summary=ev.get("summary", self.name),
            start=ev["start"],
            end=ev["end"],
            description=ev.get("description"),
        )

