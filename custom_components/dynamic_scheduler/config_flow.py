"""Config flow for the Dynamic Scheduler integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_PROVIDER_CONFIG,
    PROVIDER_FRANK,
    PROVIDER_ENTSOE,
    PROVIDER_EASYENERGY_APX,
    CONF_USE_ALL_IN,
    CONF_ENTSOE_API_KEY,
    CONF_ENTSOE_COUNTRY,
    CONF_TARIFF_RESOLUTION,
    TARIFF_RESOLUTION_HOURLY,
    TARIFF_RESOLUTION_QUARTER_HOURLY,
)


class DynamicSchedulerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """First step shown when the user adds the integration."""
        errors = {}

        provider_options = {
            PROVIDER_FRANK: "Frank Energie",
            PROVIDER_ENTSOE: "ENTSO-E Day Ahead Market",
            PROVIDER_EASYENERGY_APX: "EasyEnergy APX Market",
        }
        if user_input is not None:
            name = user_input["name"]
            provider = user_input[CONF_PROVIDER]

            provider_cfg = {}
            if provider == PROVIDER_FRANK:
                provider_cfg[CONF_USE_ALL_IN] = user_input[CONF_USE_ALL_IN]
            
            if provider == PROVIDER_ENTSOE:
                api_key = user_input.get(CONF_ENTSOE_API_KEY)
                country = user_input.get(CONF_ENTSOE_COUNTRY, "NL")

                if not api_key:
                    errors["base"] = "entsoe_api_key_missing"
                else:
                    provider_cfg[CONF_ENTSOE_API_KEY] = api_key
                    provider_cfg[CONF_ENTSOE_COUNTRY] = country or "NL"

            tariff_resolution = user_input.get(CONF_TARIFF_RESOLUTION, TARIFF_RESOLUTION_HOURLY)

            return self.async_create_entry(
                title=name,
                data={
                    "name": name,
                    CONF_PROVIDER: provider,
                    CONF_PROVIDER_CONFIG: provider_cfg,
                    CONF_TARIFF_RESOLUTION: tariff_resolution,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required("name"): cv.string,
                vol.Required(CONF_PROVIDER, default=PROVIDER_FRANK): vol.In(
                    provider_options
                ),
                # Frank-specifiek; mag leeg blijven voor ENTSO-E
                vol.Optional(CONF_USE_ALL_IN, default=True): cv.boolean,
                # ENTSO-E-specifiek; verplicht als je die provider kiest
                vol.Optional(CONF_ENTSOE_API_KEY): cv.string,
                vol.Optional(CONF_ENTSOE_COUNTRY, default="NL"): cv.string,
                vol.Optional(
                    CONF_TARIFF_RESOLUTION,
                    default=TARIFF_RESOLUTION_HOURLY,
                ): vol.In(
                    {
                        TARIFF_RESOLUTION_HOURLY: "Hourly (60-minute)",
                        TARIFF_RESOLUTION_QUARTER_HOURLY: "Quarter-hourly (15-minute)",
                    }
                ),
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
