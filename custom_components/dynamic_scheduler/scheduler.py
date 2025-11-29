"""Scheduling helpers for Dynamic Scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .price_providers import PriceRecord

# Slot = (start, end) werd vroeger gebruikt voor test-slots
SlotTuple = Tuple[datetime, datetime]

# Interne baseresolutie in minuten
BASE_SLOT_MINUTES = 15


@dataclass
class Slot:
    """Intern slot op vaste resolutie (bijv. 15 minuten)."""

    start: datetime
    end: datetime
    price: float


# ---------------------------------------------------------------------------
# NIEUWE PLANNING-LOGICA
# ---------------------------------------------------------------------------


def _expand_price_records_to_slots(
    price_records: List[PriceRecord],
    window_start: datetime,
    window_end: datetime,
    base_minutes: int = BASE_SLOT_MINUTES,
) -> List[Slot]:
    """Maak interne slots van vaste lengte (bijv. 15 min) uit PriceRecords.

    - Providers met uurprijzen leveren PriceRecord van 1 uur -> wordt 4 slots van 15 min.
    - Providers met kwartierprijzen leveren PriceRecord van 15 min -> 1 slot.
    """

    slots: List[Slot] = []

    for pr in price_records:
        # Snij record af op ons window
        rec_start = max(pr.start, window_start)
        rec_end = min(pr.end, window_end)

        # Duration in minutes
        duration_min = (rec_end - rec_start).total_seconds() / 60.0
        if duration_min <= 0:
            continue

        # Hoeveel interne stapjes passen er minimaal in?
        step = timedelta(minutes=base_minutes)

        # Ronde naar beneden op hele stappen, zodat we niet buiten rec_end vallen
        steps = int(duration_min // base_minutes)
        cur = rec_start

        for _ in range(steps):
            sub_end = cur + step
            if sub_end > rec_end:
                break
            slots.append(Slot(start=cur, end=sub_end, price=pr.value))
            cur = sub_end

    # Sorteer op starttijd
    slots.sort(key=lambda s: s.start)
    return slots


def _select_slots_non_continuous(
    slots: List[Slot],
    total_run_minutes: int,
    base_minutes: int = BASE_SLOT_MINUTES,
) -> List[Slot]:
    """Kies de goedkoopste losse blokken (non-continuous).

    - Totaalduur = total_run_minutes
    - Elk blok = base_minutes
    - We kiezen (total_run_minutes / base_minutes) goedkoopste slots.
    """

    if not slots or total_run_minutes <= 0:
        return []

    blocks_needed = (total_run_minutes + base_minutes - 1) // base_minutes

    # Sorteer op prijs (goedkoopste eerst)
    sorted_by_price = sorted(slots, key=lambda s: s.price)

    chosen = sorted_by_price[:blocks_needed]
    # Resultaat terug sorteren op tijd
    chosen.sort(key=lambda s: s.start)
    return chosen


def _select_slots_continuous(
    slots: List[Slot],
    total_run_minutes: int,
    base_minutes: int = BASE_SLOT_MINUTES,
) -> List[Slot]:
    """Kies één aaneengesloten goedkoop blok van de gewenste lengte.

    - Als we geen volledig continuous blok vinden (bij gaten in de data),
      vallen we terug op non-continuous planning.
    """

    if not slots or total_run_minutes <= 0:
        return []

    blocks_needed = (total_run_minutes + base_minutes - 1) // base_minutes

    if len(slots) < blocks_needed:
        # Niet genoeg data om continuous te vullen
        return _select_slots_non_continuous(slots, total_run_minutes, base_minutes)

    # slots zijn al gesorteerd op start
    slots_by_time = sorted(slots, key=lambda s: s.start)

    best_total_price: float | None = None
    best_start_index: int | None = None

    for i in range(len(slots_by_time)):
        # Genoeg slots over
        if i + blocks_needed > len(slots_by_time):
            break

        total_price = 0.0
        valid = True

        # Controleer dat deze window aaneengesloten is
        for j in range(blocks_needed):
            slot = slots_by_time[i + j]
            total_price += slot.price

            if j > 0:
                prev_slot = slots_by_time[i + j - 1]
                if slot.start != prev_slot.end:
                    valid = False
                    break

        if not valid:
            continue

        if best_total_price is None or total_price < best_total_price:
            best_total_price = total_price
            best_start_index = i

    if best_start_index is None:
        # Geen volledig continuous blok -> fallback
        return _select_slots_non_continuous(slots, total_run_minutes, base_minutes)

    best_slots = slots_by_time[best_start_index : best_start_index + blocks_needed]
    return best_slots


def _merge_slots_to_events(slots: List[Slot]) -> List[Dict[str, Any]]:
    """Merge aaneengesloten slots tot langere kalender-events.

    Alle slots moeten al op start gesorteerd zijn.
    """

    if not slots:
        return []

    slots = sorted(slots, key=lambda s: s.start)

    events: List[Dict[str, Any]] = []

    current_start = slots[0].start
    current_end = slots[0].end

    for slot in slots[1:]:
        if slot.start == current_end:
            # Sluit direct aan -> verleng huidig event
            current_end = slot.end
        else:
            # Nieuwe event
            events.append(
                {
                    "start": current_start,
                    "end": current_end,
                    "summary": "Dynamic run",
                    "description": "Scheduled by Dynamic Scheduler",
                }
            )
            current_start = slot.start
            current_end = slot.end

    # Laatste flushen
    events.append(
        {
            "start": current_start,
            "end": current_end,
            "summary": "Dynamic run",
            "description": "Scheduled by Dynamic Scheduler",
        }
    )

    return events


async def schedule_calendar_from_prices(
    hass: HomeAssistant,
    calendar_entity_id: str,
    price_records: List[PriceRecord],
    window_start: datetime,
    window_end: datetime,
    total_run_minutes: int,
    continuous: bool,
    clear_existing: bool = True,
    base_minutes: int = BASE_SLOT_MINUTES,
) -> None:
    """Hoofdfunctie: maak een schema op basis van prijzen en schrijf het naar de kalender.

    - price_records: output van een PriceProvider
    - window_start, window_end: tijdvenster waarin gepland mag worden
    - total_run_minutes: totale looptijd (bijv. 180 = 3 uur)
    - continuous: True => één aaneengesloten blok, False => losse goedkoopste blokken
    - base_minutes: interne slot-grootte (standaard 15 min)
    """

    # 1) Prijzen omzetten naar interne slots
    slots = _expand_price_records_to_slots(
        price_records=price_records,
        window_start=window_start,
        window_end=window_end,
        base_minutes=base_minutes,
    )

    if not slots:
        # Geen data -> niets te plannen
        domain = hass.data.setdefault(DOMAIN, {})
        events_by_calendar: Dict[str, Any] = domain.setdefault("events_by_calendar", {})
        if clear_existing:
            events_by_calendar[calendar_entity_id] = []
        return

    # 2) Slots selecteren op basis van continuous / non-continuous
    if continuous:
        chosen_slots = _select_slots_continuous(
            slots=slots,
            total_run_minutes=total_run_minutes,
            base_minutes=base_minutes,
        )
    else:
        chosen_slots = _select_slots_non_continuous(
            slots=slots,
            total_run_minutes=total_run_minutes,
            base_minutes=base_minutes,
        )

    # 3) Merge de gekozen slots tot events
    events = _merge_slots_to_events(chosen_slots)

    # 4) Events wegschrijven in hass.data[DOMAIN]["events_by_calendar"]
    domain = hass.data.setdefault(DOMAIN, {})
    events_by_calendar: Dict[str, Any] = domain.setdefault("events_by_calendar", {})

    if clear_existing:
        events_by_calendar[calendar_entity_id] = events
    else:
        existing = events_by_calendar.get(calendar_entity_id, [])
        events_by_calendar[calendar_entity_id] = existing + events



#Testfunctie oud: Bewaren voor debug. 
async def store_test_slots_for_calendar(
    hass: HomeAssistant,
    calendar_entity_id: str,
    start: datetime,
    total_run_minutes: int,
    slot_length_minutes: int,
    clear_existing: bool = True,
) -> None:
    """Create simple back-to-back slots starting at 'start' and store them.

    LET OP: dit is de oude testfunctie. Voor de echte scheduler:
    gebruik schedule_calendar_from_prices(...) vanuit __init__.py.
    """

    slots: List[SlotTuple] = []
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
                "summary": "Test slot",
                "description": "Dynamic Scheduler test",
            }
        )

    events_by_calendar[calendar_entity_id] = events
