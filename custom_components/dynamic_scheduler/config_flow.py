"""Config flow for the Dynamic Scheduler integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class DynamicSchedulerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """First step shown when the user adds the integration."""
        if user_input is not None:
            # Create a config entry with no data yet
            return self.async_create_entry(
                title="Dynamic Scheduler",
                data={}
            )

        # First-time form: empty form (just a submit button)
        return self.async_show_form(step_id="user", data_schema=None)


@callback
def async_get_options_flow(config_entry):
    """Return the options flow handler."""
    return DynamicSchedulerOptionsFlow(config_entry)


class DynamicSchedulerOptionsFlow(config_entries.OptionsFlow):
    """Placeholder options flow (we fill this later)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Dynamic Scheduler options",
                data={}
            )

        return self.async_show_form(step_id="init", data_schema=None)
