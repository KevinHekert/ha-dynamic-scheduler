"""Price provider interface and factory for Dynamic Scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, List, Any, Dict

from homeassistant.core import HomeAssistant

from ..const import (
    CONF_PROVIDER,
    CONF_PROVIDER_CONFIG,
    PROVIDER_FRANK,
    CONF_USE_ALL_IN,
)


@dataclass
class PriceRecord:
    start: datetime
    end: datetime
    value: float


class PriceProvider(Protocol):
    """Protocol for price providers."""

    async def async_get_prices(
        self,
        hass: HomeAssistant,
        now: datetime,
        window_end: datetime,
    ) -> List[PriceRecord]:
        ...


def create_price_provider(config: Dict[str, Any]) -> PriceProvider:
    """Factory that creates a PriceProvider from config entry data.

    Expected config structure:
    {
      CONF_PROVIDER: "frank_energie",
      CONF_PROVIDER_CONFIG: {
        "use_all_in": True
      }
    }
    """
    provider_id: str = config[CONF_PROVIDER]
    provider_cfg: Dict[str, Any] = config.get(CONF_PROVIDER_CONFIG, {})

    if provider_id == PROVIDER_FRANK:
        from .frank_energie import FrankEnergyProvider

        use_all_in = provider_cfg.get(CONF_USE_ALL_IN, True)
        return FrankEnergyProvider(use_all_in=use_all_in)

    raise ValueError(f"Unknown price provider id: {provider_id}")
