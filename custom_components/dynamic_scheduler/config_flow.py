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

    def __init__(self) -> None:
        self._name: str | None = None
        self._provider: str | None = None

    # ------------------------------------------------------------------
    # STAP 1: naam + provider kiezen
    # ------------------------------------------------------------------
    async def async_step_user(self, user_input=None):
        """Eerste stap: vraag om naam en provider."""
        provider_options = {
            PROVIDER_FRANK: "Frank Energie",
            PROVIDER_ENTSOE: "ENTSO-E day-ahead (marktprijs)",
            PROVIDER_EASYENERGY_APX: "EasyEnergy APX (marktprijs)",
        }

        if user_input is not None:
            self._name = user_input["name"]
            self._provider = user_input[CONF_PROVIDER]

            if self._provider == PROVIDER_FRANK:
                return await self.async_step_frank()
            if self._provider == PROVIDER_ENTSOE:
                return await self.async_step_entsoe()
            if self._provider == PROVIDER_EASYENERGY_APX:
                return await self.async_step_easyenergy()

            return self.async_abort(reason="unknown_provider")

        data_schema = vol.Schema(
            {
                vol.Required("name"): cv.string,
                vol.Required(CONF_PROVIDER, default=PROVIDER_FRANK): vol.In(
                    provider_options
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors={},
        )

    # ------------------------------------------------------------------
    # STAP 2A: FRANK-OPTIES
    # ------------------------------------------------------------------
    async def async_step_frank(self, user_input=None):
        """Tweede stap voor Frank Energie-specifieke opties."""
        errors = {}

        if user_input is not None:
            use_all_in = user_input.get(CONF_USE_ALL_IN, True)
            tariff_resolution = user_input.get(
                CONF_TARIFF_RESOLUTION, TARIFF_RESOLUTION_HOURLY
            )

            provider_cfg = {CONF_USE_ALL_IN: use_all_in}

            return self.async_create_entry(
                title=self._name or "Dynamic Scheduler",
                data={
                    "name": self._name,
                    CONF_PROVIDER: self._provider,
                    CONF_PROVIDER_CONFIG: provider_cfg,
                    CONF_TARIFF_RESOLUTION: tariff_resolution,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_USE_ALL_IN, default=True): cv.boolean,
                vol.Optional(
                    CONF_TARIFF_RESOLUTION, default=TARIFF_RESOLUTION_HOURLY
                ): vol.In(
                    {
                        TARIFF_RESOLUTION_HOURLY: "Hourly (60-minute prices)",
                        TARIFF_RESOLUTION_QUARTER_HOURLY: "Quarter-hourly (15-minute prices)",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="frank",
            data_schema=data_schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # STAP 2B: ENTSO-E OPTIES
    # ------------------------------------------------------------------
    async def async_step_entsoe(self, user_input=None):
        """Tweede stap voor ENTSO-E-specifieke opties."""
        errors = {}

        if user_input is not None:
            api_key = user_input.get(CONF_ENTSOE_API_KEY)
            country = user_input.get(CONF_ENTSOE_COUNTRY, "NL")
            tariff_resolution = user_input.get(
                CONF_TARIFF_RESOLUTION, TARIFF_RESOLUTION_HOURLY
            )

            if not api_key:
                errors["base"] = "entsoe_api_key_missing"
            else:
                provider_cfg = {
                    CONF_ENTSOE_API_KEY: api_key,
                    CONF_ENTSOE_COUNTRY: country or "NL",
                }

                return self.async_create_entry(
                    title=self._name or "Dynamic Scheduler",
                    data={
                        "name": self._name,
                        CONF_PROVIDER: self._provider,
                        CONF_PROVIDER_CONFIG: provider_cfg,
                        CONF_TARIFF_RESOLUTION: tariff_resolution,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ENTSOE_API_KEY): cv.string,
                vol.Optional(CONF_ENTSOE_COUNTRY, default="NL"): cv.string,
                vol.Optional(
                    CONF_TARIFF_RESOLUTION, default=TARIFF_RESOLUTION_HOURLY
                ): vol.In(
                    {
                        TARIFF_RESOLUTION_HOURLY: "Hourly (60-minute prices)",
                        TARIFF_RESOLUTION_QUARTER_HOURLY: "Quarter-hourly (15-minute prices)",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="entsoe",
            data_schema=data_schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # STAP 2C: EASYENERGY OPTIES
    # ------------------------------------------------------------------
    async def async_step_easyenergy(self, user_input=None):
        """Tweede stap voor EasyEnergy APX."""

        if user_input is not None:
            tariff_resolution = user_input.get(
                CONF_TARIFF_RESOLUTION, TARIFF_RESOLUTION_HOURLY
            )

            return self.async_create_entry(
                title=self._name or "Dynamic Scheduler",
                data={
                    "name": self._name,
                    CONF_PROVIDER: self._provider,
                    CONF_PROVIDER_CONFIG: {},
                    CONF_TARIFF_RESOLUTION: tariff_resolution,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TARIFF_RESOLUTION, default=TARIFF_RESOLUTION_HOURLY
                ): vol.In(
                    {
                        TARIFF_RESOLUTION_HOURLY: "Hourly (60-minute prices)",
                        TARIFF_RESOLUTION_QUARTER_HOURLY: "Quarter-hourly (15-minute prices)",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="easyenergy",
            data_schema=data_schema,
            errors={},
        )


# ----------------------------------------------------------------------
# OPTIONS FLOW (nog minimaal)
# ----------------------------------------------------------------------
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
