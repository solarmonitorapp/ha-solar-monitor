"""Fetches /api/now on a schedule, for every entity at once."""

from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarMonitorClient, SolarMonitorError
from .const import DOMAIN, LOGGER, SCAN_INTERVAL, STALE_AFTER_SEC

type SolarMonitorConfigEntry = ConfigEntry[SolarMonitorCoordinator]


class SolarMonitorCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holds the latest /api/now."""

    config_entry: SolarMonitorConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SolarMonitorConfigEntry,
        client: SolarMonitorClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=f"Solar Monitor {client.host}",
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    @property
    def stale(self) -> bool:
        """Whether the latest reading is too old to show as right now."""
        age = self.data.get("ageSec")
        return isinstance(age, (int, float)) and age > STALE_AFTER_SEC

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.now()
        except SolarMonitorError as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"error": str(error)},
            ) from error
        # ok is false until the monitor has read the gateway once, e.g. just
        # after it boots. There is nothing to show yet.
        if not data.get("ok"):
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="no_reading"
            )
        return data
