"""Binary sensors: exporting, and each panel's health."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SolarMonitorConfigEntry
from .entity import SolarMonitorEntity, SolarMonitorPanelEntity, field, panels_by_serial

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SolarMonitorBinarySensorDescription(BinarySensorEntityDescription):
    """Where a binary sensor's value sits in /api/now (or in one panel's entry)."""

    value_fn: Callable[[dict[str, Any]], bool | None]


SYSTEM_BINARY_SENSORS: tuple[SolarMonitorBinarySensorDescription, ...] = (
    SolarMonitorBinarySensorDescription(
        key="exporting",
        translation_key="exporting",
        # Without a grid meter there is no telling.
        value_fn=lambda data: (
            field(data, "power", "exporting")
            if field(data, "power", "hasGrid")
            else None
        ),
    ),
)

PANEL_BINARY_SENSORS: tuple[SolarMonitorBinarySensorDescription, ...] = (
    SolarMonitorBinarySensorDescription(
        # The health signal: whether the gateway is still hearing from this
        # inverter. Not the gateway's STATE, which reads "error" every night.
        key="reporting",
        translation_key="reporting",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda panel: panel.get("reporting"),
    ),
    SolarMonitorBinarySensorDescription(
        # Under 85% of the typical panel, judged only in daylight.
        key="weak",
        translation_key="weak",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda panel: panel.get("weak"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors, and add panels as the gateway starts listing them."""
    coordinator = entry.runtime_data
    async_add_entities(
        SolarMonitorBinarySensor(coordinator, description)
        for description in SYSTEM_BINARY_SENSORS
    )

    known: set[str] = set()

    @callback
    def add_new_panels() -> None:
        new = panels_by_serial(coordinator.data).keys() - known
        known.update(new)
        async_add_entities(
            SolarMonitorPanelBinarySensor(coordinator, description, serial)
            for serial in new
            for description in PANEL_BINARY_SENSORS
        )

    add_new_panels()
    entry.async_on_unload(coordinator.async_add_listener(add_new_panels))


class SolarMonitorBinarySensor(SolarMonitorEntity, BinarySensorEntity):
    """A system binary sensor."""

    entity_description: SolarMonitorBinarySensorDescription

    @property
    @override
    def available(self) -> bool:
        # Exporting is a right-now reading, like the power sensors.
        return super().available and not self.coordinator.stale

    @property
    @override
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)


class SolarMonitorPanelBinarySensor(SolarMonitorPanelEntity, BinarySensorEntity):
    """A panel binary sensor."""

    entity_description: SolarMonitorBinarySensorDescription

    @property
    @override
    def is_on(self) -> bool | None:
        panel = self.panel
        return None if panel is None else self.entity_description.value_fn(panel)
