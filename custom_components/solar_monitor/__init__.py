"""The Solar Monitor integration."""

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarMonitorClient
from .coordinator import SolarMonitorConfigEntry, SolarMonitorCoordinator
from .entity import system_device_info

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SolarMonitorConfigEntry) -> None:
    """Set up a Solar Monitor from a config entry."""
    client = SolarMonitorClient(entry.data[CONF_HOST], async_get_clientsession(hass))
    coordinator = SolarMonitorCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Panels link to this device by its id, so it has to exist before any
    # platform adds them.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **system_device_info(coordinator)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: SolarMonitorConfigEntry) -> None:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
