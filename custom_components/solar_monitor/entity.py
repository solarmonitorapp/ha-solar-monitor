"""Base entities: the system as a whole, and one device per panel."""

from typing import Any, override

from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarMonitorCoordinator


def field(data: dict[str, Any], *path: str) -> Any:
    """Return data[a][b]..., or None anywhere along the way.

    The monitor sends null for anything it does not know (a meter that is not
    fitted, a panel that has not reported), and None reaches Home Assistant as
    "unknown", which is what it means.
    """
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def panels_by_serial(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The panel list, keyed by inverter serial, the only stable key it has."""
    return {
        item["serial"]: item
        for item in field(data, "panels", "items") or []
        if item.get("serial")
    }


def system_device_info(coordinator: SolarMonitorCoordinator) -> DeviceInfo:
    """The Solar Monitor device, which the panels hang off."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
        name="Solar Monitor",
        manufacturer="Solar Monitor",
        model="Solar Monitor",
        sw_version=coordinator.data.get("version"),
        configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}/",
    )


class SolarMonitorEntity(CoordinatorEntity[SolarMonitorCoordinator]):
    """An entity on the Solar Monitor device itself."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SolarMonitorCoordinator, description: EntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"
        self._attr_device_info = system_device_info(coordinator)


class SolarMonitorPanelEntity(CoordinatorEntity[SolarMonitorCoordinator]):
    """An entity on one panel's micro-inverter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarMonitorCoordinator,
        description: EntityDescription,
        serial: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.serial = serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"Panel {serial[-6:]}",
            manufacturer="SunPower",
            model="Micro-inverter",
            serial_number=serial,
            via_device_id=dr.async_get_device_id_by_identifier(
                coordinator.hass,
                (DOMAIN, coordinator.config_entry.unique_id),
                config_entry_id=coordinator.config_entry.entry_id,
            ),
        )

    @property
    def panel(self) -> dict[str, Any] | None:
        """This panel's entry in the latest reading, if it is still listed."""
        return panels_by_serial(self.coordinator.data).get(self.serial)

    @property
    @override
    def available(self) -> bool:
        return super().available and self.panel is not None
