"""Sensor platform for the British Gas integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COMMODITY_ELECTRICITY, COMMODITY_GAS, DOMAIN
from .coordinator import BritishGasCoordinator
from .entity import BritishGasEntity

PARALLEL_UPDATES = 0

_COMMODITY_ICONS: dict[str, str] = {
    COMMODITY_GAS: "mdi:gas-burner",
    COMMODITY_ELECTRICITY: "mdi:lightning-bolt",
}


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up British Gas sensors from a config entry."""
    coordinator: BritishGasCoordinator = entry.runtime_data

    async_add_entities(
        entity
        for meter_point_id in coordinator.data
        for entity in (
            BritishGasBalanceSensor(coordinator, meter_point_id),
            BritishGasLastUpdatedSensor(coordinator, meter_point_id),
        )
    )


class BritishGasBalanceSensor(BritishGasEntity, SensorEntity):
    """Sensor representing the prepayment balance for a British Gas meter."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_translation_key = "balance"

    def __init__(
        self,
        coordinator: BritishGasCoordinator,
        meter_point_id: int,
    ) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, meter_point_id)
        meter_point = coordinator.data[meter_point_id]

        self._attr_unique_id = f"{meter_point.meter_point_reference}_balance"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, meter_point.meter_point_reference)},
            manufacturer="British Gas",
            name=f"{meter_point.address} {meter_point.commodity}",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current credit balance in GBP."""
        return self._meter_point.balance

    @property
    def icon(self) -> str:
        """Return an icon appropriate for the commodity type."""
        return _COMMODITY_ICONS.get(self._meter_point.commodity, "mdi:currency-gbp")

    @property
    def extra_state_attributes(self) -> dict[str, str | float | None]:
        """Return meter reference, commodity type, and any debt balance."""
        meter_point = self._meter_point
        return {
            "meter_point_reference": meter_point.meter_point_reference,
            "commodity": meter_point.commodity,
            "debt": meter_point.debt,
        }


class BritishGasLastUpdatedSensor(BritishGasEntity, SensorEntity):
    """Sensor representing the last balance update time for a British Gas meter."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "last_updated"

    def __init__(
        self,
        coordinator: BritishGasCoordinator,
        meter_point_id: int,
    ) -> None:
        """Initialize the last updated sensor."""
        super().__init__(coordinator, meter_point_id)
        meter_point = coordinator.data[meter_point_id]

        self._attr_unique_id = f"{meter_point.meter_point_reference}_last_updated"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, meter_point.meter_point_reference)},
            manufacturer="British Gas",
            name=f"{meter_point.address} {meter_point.commodity}",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the UTC timestamp of the last balance reading."""
        return self._meter_point.balance_timestamp
