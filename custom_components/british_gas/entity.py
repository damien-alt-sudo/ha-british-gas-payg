"""Base entity for the British Gas integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BritishGasCoordinator, MeterPointBalance


class BritishGasEntity(CoordinatorEntity[BritishGasCoordinator]):
    """Base class for British Gas entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BritishGasCoordinator,
        meter_point_id: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._meter_point_id = meter_point_id

    @property
    def _meter_point(self) -> MeterPointBalance:
        """Return the meter point data from the coordinator."""
        return self.coordinator.data[self._meter_point_id]
