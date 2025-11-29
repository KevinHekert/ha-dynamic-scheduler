"""Config flow for the Dynamic Scheduler integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN


class DynamicSchedulerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """First step shown when the user adds the integration."""
        errors = {}

        if user_input is not None:
            name = user_input["name"]

            return self.async_create_entry(
                title=name,
                data={
                    "name": name,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required("name"): cv.string,  # bijv. "Auto", "Wasdroger"
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


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
                data={},
            )

        return self.async_show_form(step_id="init", data_schema=None)
