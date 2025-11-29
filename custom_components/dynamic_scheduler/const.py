"""Constants for the Dynamic Scheduler integration."""

DOMAIN = "dynamic_scheduler"

# Provider keys
CONF_PROVIDER = "provider"
CONF_PROVIDER_CONFIG = "provider_config"

# Supported providers
PROVIDER_FRANK = "frank_energie"
PROVIDER_ENTSOE = "entsoe_day_ahead"
PROVIDER_EASYENERGY_APX = "easyenergy_apx"

# Frank-specifieke opties
# True = prijs inclusief opslag / all-in, False = kale marktprijs (afhankelijk van implementatie)
CONF_USE_ALL_IN = "use_all_in"  # True = priceIncludingMarkup, False = marketPrice

# ENTSO-E-specifieke opties
CONF_ENTSOE_API_KEY = "entsoe_api_key"
CONF_ENTSOE_COUNTRY = "entsoe_country"  # bijv. "NL"
