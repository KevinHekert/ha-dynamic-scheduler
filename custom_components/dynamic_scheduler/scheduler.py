"""Simple helper to store test slots as calendar events."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Slot = (start, end)
Slot = Tuple[datetime, datetime]


async def store_test_slots_for_calendar(
    hass: HomeAssistant,
    calendar_entity_id: str,
    start: datetime,
    total_run_minutes: int,
    slot_length_minutes: int,
    clear_existing: bool = True,
) -> None:
    """Create simple back-to-back slots starting at 'start' and store them."""

    # Bepaal hoeveel slots we nodig hebben
    slots: List[Slot] = []
    remaining = total_run_minutes
    cur = start

    while remaining > 0:
        length = min(slot_length_minutes, remaining)
        end = cur + timedelta(minutes=length)
        slots.append((cur, end))
        cur = end
        remaining -= length

    domain = hass.data.setdefault(DOMAIN, {})
    events_by_calendar: Dict[str, Any] = domain.setdefault("events_by_calendar", {})

    events: List[Dict[str, Any]] = [] if clear_existing else events_by_calendar.get(
        calendar_entity_id, []
    )

    for s, e in slots:
        events.append(
            {
                "start": s,
                "end": e,
                "summary": f"Test slot",
                "description": "Dynamic Scheduler test",
            }
        )

    events_by_calendar[calendar_entity_id] = events
