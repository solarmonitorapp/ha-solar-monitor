"""Sensors for the system and for each panel."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import SolarMonitorConfigEntry
from .entity import SolarMonitorEntity, SolarMonitorPanelEntity, field, panels_by_serial

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SolarMonitorSensorDescription(SensorEntityDescription):
    """Where a sensor's value sits in /api/now (or in one panel's entry)."""

    value_fn: Callable[[dict[str, Any]], StateType]
    # A right-now reading, unavailable once the reading is stale.
    live: bool = False


def _power(key: str, *path: str) -> SolarMonitorSensorDescription:
    return SolarMonitorSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        value_fn=lambda data: field(data, *path),
        live=True,
    )


def _energy(key: str, *path: str) -> SolarMonitorSensorDescription:
    # The lifetime counters are the meters' own totals, so Home Assistant can
    # work out any period from them, the Energy dashboard included.
    return SolarMonitorSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: field(data, *path),
    )


SYSTEM_SENSORS: tuple[SolarMonitorSensorDescription, ...] = (
    _power("production", "power", "productionKw"),
    # Positive while buying from the grid, negative while selling to it.
    _power("grid", "power", "gridKw"),
    # Production plus grid. A battery the gateway does not know about counts
    # as load while it charges (API.md, Batteries).
    _power("load", "power", "loadKw"),
    _energy("produced_today", "today", "producedKwh"),
    _energy("produced_lifetime", "lifetime", "producedKwh"),
    # null when the gateway cannot split the grid into bought and sold.
    _energy("bought_lifetime", "lifetime", "boughtKwh"),
    _energy("sold_lifetime", "lifetime", "soldKwh"),
    SolarMonitorSensorDescription(
        key="panels_reporting",
        translation_key="panels_reporting",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: field(data, "panels", "reporting"),
    ),
    SolarMonitorSensorDescription(
        key="reading_age",
        translation_key="reading_age",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: field(data, "ageSec"),
    ),
    SolarMonitorSensorDescription(
        key="gateway_firmware",
        translation_key="gateway_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: field(data, "gateway", "firmware"),
    ),
)

PANEL_SENSORS: tuple[SolarMonitorSensorDescription, ...] = (
    _power("panel_power", "kw"),
    _energy("panel_lifetime", "lifetimeKwh"),
    SolarMonitorSensorDescription(
        # The micro-inverter's heatsink, not the panel's surface.
        key="inverter_temperature",
        translation_key="inverter_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda panel: panel.get("tempC"),
    ),
    SolarMonitorSensorDescription(
        key="dc_voltage",
        translation_key="dc_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_registry_enabled_default=False,
        value_fn=lambda panel: panel.get("dcVolts"),
    ),
    SolarMonitorSensorDescription(
        key="dc_current",
        translation_key="dc_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_registry_enabled_default=False,
        value_fn=lambda panel: panel.get("dcAmps"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors, and add panels as the gateway starts listing them."""
    coordinator = entry.runtime_data
    async_add_entities(
        SolarMonitorSensor(coordinator, description) for description in SYSTEM_SENSORS
    )

    known: set[str] = set()

    @callback
    def add_new_panels() -> None:
        new = panels_by_serial(coordinator.data).keys() - known
        known.update(new)
        async_add_entities(
            SolarMonitorPanelSensor(coordinator, description, serial)
            for serial in new
            for description in PANEL_SENSORS
        )

    add_new_panels()
    entry.async_on_unload(coordinator.async_add_listener(add_new_panels))


class SolarMonitorSensor(SolarMonitorEntity, SensorEntity):
    """A system sensor."""

    entity_description: SolarMonitorSensorDescription

    @property
    @override
    def available(self) -> bool:
        return super().available and not (
            self.entity_description.live and self.coordinator.stale
        )

    @property
    @override
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)


class SolarMonitorPanelSensor(SolarMonitorPanelEntity, SensorEntity):
    """A panel sensor."""

    entity_description: SolarMonitorSensorDescription

    @property
    @override
    def available(self) -> bool:
        return super().available and not (
            self.entity_description.live and self.coordinator.stale
        )

    @property
    @override
    def native_value(self) -> StateType:
        panel = self.panel
        return None if panel is None else self.entity_description.value_fn(panel)
