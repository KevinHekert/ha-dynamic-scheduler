# HA Dynamic Scheduler

Home Assistant custom integration that calculates and schedules the **cheapest time slots** for flexible loads based on **day-ahead energy prices**.

Use it to automatically schedule:

- EV charging
- Washing machines & dryers
- Boilers / (boost) heaters
- Heat pumps & buffer tanks
- Any other time-shiftable load

The integration exposes a **calendar entity** and a **schedule service**.  
You tell it: “run for *N* hours before *deadline*”, it fills the calendar with the **cheapest slots**.  
Your automations simply follow the calendar.

Repository: <https://github.com/KevinHekert/ha-dynamic-scheduler>

---

## Features

- **Price-optimised scheduling**  
  Uses day-ahead prices and picks the cheapest available time slots between “now” and a given deadline.

- **Deadline-based runtime**  
  “Run for 3 hours before 07:00” – no need to manually calculate start times.

- **Continuous or non-continuous runs**  
  - Single continuous block (e.g. 03:00–06:00), or  
  - Multiple scattered cheap slots (e.g. 12 × 15-minute slots at the lowest prices).

- **Calendar-driven control**  
  Each instance creates its own **calendar entity**.  
  Automations trigger on calendar events (start/end).

- **Multiple price providers** (via `price_providers/`):
  - Frank Energie  
  - ENTSO-E Day Ahead market  
  - EasyEnergy APX (JSON / XML)

- **Fixed 15-minute internal resolution**  
  Supports both hourly and 15-minute tariffs; all prices are normalised into 15-minute “slots”.

---

## Installation

### 1. Install via HACS (recommended)

1. Make sure you have [HACS](https://hacs.xyz) installed in Home Assistant.
2. In Home Assistant, go to:  
   **HACS → Integrations**.
3. Click the **⋮ (three dots)** in the top right → **Custom repositories**.
4. Add this repository:
   - URL: `https://github.com/KevinHekert/ha-dynamic-scheduler`
   - Category: `Integration`
5. After adding the repository, search within HACS → Integrations for **Dynamic Scheduler**.
6. Install the integration from HACS.
7. Restart Home Assistant.

### 2. Manual installation (alternative)

1. Locate your Home Assistant `config` directory (where `configuration.yaml` lives).
2. Create the `custom_components` folder if it does not exist:

       config/custom_components/

3. Download this repository (ZIP) or clone it:

       cd /path/to/your/config
       git clone https://github.com/KevinHekert/ha-dynamic-scheduler.git

4. Copy the integration into `custom_components` (adjust paths if needed):

       config/
         custom_components/
           dynamic_scheduler/
             __init__.py
             manifest.json
             const.py
             config_flow.py
             calendar.py
             scheduler.py
             services.yaml
             price_providers/
               __init__.py
               frank_energie.py
               entsoe_market.py
               easyenergy_apx.py

5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and search for **Dynamic Scheduler**.

---

## How it works (high level)

1. You add the integration via the Home Assistant UI and select a **price provider**.
2. The integration creates a **calendar entity**, for example `calendar.ev_charger`.
3. You call the service `dynamic_scheduler.schedule` with:
   - A **calendar entity**
   - A **deadline time** (by when the run must be finished)
   - A **runtime** (total duration to run)
   - Optional flags: continuous / non-continuous, clear existing events, etc.
4. The integration:
   - Fetches prices from the selected provider for the window `[now, deadline)`.
   - Splits these into internal 15-minute slots.
   - Picks the cheapest slots that satisfy your runtime and continuity settings.
   - Merges adjacent slots into events and writes them into the calendar.

Your automations react on **calendar events** to switch devices on and off.

---

## Configuration

Configuration is done via the config flow in the Home Assistant UI.

### Adding an instance

1. Go to **Settings → Devices & services**.
2. Click **“Add integration”**.
3. Search for **Dynamic Scheduler**.
4. Follow the wizard:

You configure:

- **Name**  
  Friendly name for this schedule.  
  Used as the calendar’s name (`calendar.<slugified_name>`).

- **Price provider**  
  One of:
  - `Frank Energie`
  - `ENTSO-E Day Ahead`
  - `EasyEnergy APX`

Then provider-specific options are shown.

### Provider-specific options

#### Frank Energie

- **Use all-in price** (`use_all_in`)  
  - `true`: use Frank’s “all-in” tariffs (including markup/fees depending on implementation).  
  - `false`: use base/market prices.

#### ENTSO-E Day Ahead

- **ENTSO-E API key** (`entsoe_api_key`) – required  
- **Country / bidding zone** (`entsoe_country`) – default `NL`, configurable.

If the API key is missing or invalid, price retrieval fails and an error is logged in Home Assistant.

#### EasyEnergy APX

- No additional configuration.  
- The provider handles both JSON and XML responses from EasyEnergy’s APX endpoint.

---

## Entities

Each configured instance creates **one calendar entity**.

Example:

- Name in config flow: `EV Charger`
- Calendar entity: `calendar.ev_charger`

The calendar:

- Contains events for the scheduled run windows.
- Exposes the next upcoming event as `event` (standard Home Assistant calendar behaviour).
- Can be shown in Lovelace using any calendar card.
- Can be used in automations, scripts and templates.

---

## Service: `dynamic_scheduler.schedule`

The core of the integration is a single service.

### Service name

    dynamic_scheduler.schedule

### Service fields

| Field                | Type        | Required | Description |
|----------------------|------------|----------|-------------|
| `calendar_entity_id` | `calendar.*` | yes     | Calendar entity created by Dynamic Scheduler. |
| `deadline_time`      | `HH:MM:SS` | yes      | Time of day by which the run must be **finished** (next occurrence). |
| `runtime`            | `HH:MM:SS` | yes      | Total runtime to schedule (e.g. `03:00:00` = 3 hours). |
| `slot_length_minutes`| integer    | no       | Reserved for compatibility; internal resolution is fixed at 15 minutes. |
| `continuous`         | boolean    | no       | `true` = one continuous block; `false` = scattered cheapest slots. Default: `false`. |
| `clear_existing`     | boolean    | no       | `true` = remove existing events for this calendar before adding new ones. Default: `true`. |

#### Deadline logic

- `deadline_time` is interpreted as the next occurrence of that time:
  - If the specified time is still in the future today → deadline is today.
  - If it has already passed today → deadline is tomorrow at that time.
- Prices are requested for the window from “now” up to that deadline.

#### Runtime logic

- `runtime` is converted into minutes.
- With 15-minute slot size, 3 hours runtime equals 12 slots.

### Example: continuous run

    service: dynamic_scheduler.schedule
    data:
      calendar_entity_id: calendar.ev_charger
      deadline_time: "07:00:00"
      runtime: "03:00:00"
      continuous: true
      clear_existing: true

This:

1. Fetches prices from **now** until `07:00` (today/tomorrow).
2. Finds the **cheapest continuous 3-hour block** (12 consecutive 15-minute slots).
3. Creates one or more calendar events on `calendar.ev_charger`.

### Example: scattered cheap slots

    service: dynamic_scheduler.schedule
    data:
      calendar_entity_id: calendar.boiler
      deadline_time: "23:00:00"
      runtime: "02:00:00"
      continuous: false
      clear_existing: true

This:

1. Fetches prices from **now** until `23:00`.
2. Selects the **8 cheapest 15-minute slots** in that window.
3. Merges adjacent slots into events and writes them to `calendar.boiler`.

---

## Algorithm overview

All price data is normalised into 15-minute “slots”. Selection is done at that level.

1. **Price records → 15-minute slots**
   - Hourly prices → 4 × 15-minute slots.
   - Quarter-hour prices → 1 × 15-minute slot.
   - All slots are clipped to the `[now, deadline)` window.

2. **Non-continuous mode**
   - Sort all slots by price (ascending).
   - Pick `N = runtime_minutes / 15` cheapest slots.

3. **Continuous mode**
   - Slide a window of size `N` over the time-ordered slots.
   - Only consider windows where each slot is directly adjacent to the previous one (no gaps).
   - Select the window with the lowest total price.
   - If no valid continuous window exists (e.g. gaps), fall back to non-continuous mode.

4. **Merge and store**
   - Adjacent selected slots are merged into single calendar events.
   - Events are stored under the calendar entity and exposed through the standard Home Assistant calendar API.

---

## Using the calendar in automations

Because this integration exposes a **calendar entity**, you can use Home Assistant’s built-in calendar triggers.

### Start a device when a scheduled run begins

    alias: Start EV charger when Dynamic Scheduler event starts
    trigger:
      - platform: calendar
        event: start
        entity_id: calendar.ev_charger
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger
    mode: single

### Stop the device when the run ends

    alias: Stop EV charger when Dynamic Scheduler event ends
    trigger:
      - platform: calendar
        event: end
        entity_id: calendar.ev_charger
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.ev_charger
    mode: single

These triggers can be combined with conditions, for example:

- Only run if outside temperature is above or below a threshold.
- Only run if battery state-of-charge is above or below a value.
- Only run when someone is home or away, etc.

---


## Development

1. Clone the repository:

       git clone https://github.com/KevinHekert/ha-dynamic-scheduler.git
       cd ha-dynamic-scheduler

2. Ensure the integration is available in your Home Assistant test instance under:

       <config>/custom_components/dynamic_scheduler/

3. Enable debug logging while developing:

       logger:
         default: warning
         logs:
           custom_components.dynamic_scheduler: debug
           custom_components.dynamic_scheduler.price_providers: debug

4. Restart Home Assistant.
5. Trigger the `dynamic_scheduler.schedule` service via **Developer Tools → Services** and inspect the logs.

---

## Issues and contributions

- Issues and bug reports:  
  <https://github.com/KevinHekert/ha-dynamic-scheduler/issues>

Pull requests are welcome.

---

## License
No license