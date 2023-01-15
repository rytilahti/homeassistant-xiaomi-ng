"""Support for Xiaomi Miio binary sensors."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from .device import XiaomiMiioEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)


class XiaomiBinarySensor(XiaomiMiioEntity, BinarySensorEntity):
    """Representation of a Xiaomi Humidifier binary sensor."""

    _attr_has_entity_name = True
    entity_description: BinarySensorEntityDescription

    def __init__(self, device, sensor, entry, coordinator):
        """Initialize the entity."""
        self._name = sensor.name
        self._property = sensor.property
        unique_id = f"{entry.unique_id}_binarysensor_{sensor.id}"

        super().__init__(device, entry, unique_id, coordinator)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(sensor.extras.get("entity_category", "diagnostic"))
        description = BinarySensorEntityDescription(
            key=sensor.id,
            name=sensor.name,
            icon=sensor.extras.get("icon"),
            device_class=sensor.extras.get("device_class"),
            entity_category=category,
            entity_registry_enabled_default=sensor.extras.get("enabled_default", True),
        )

        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(getattr(self.coordinator.data, self._property))
        _LOGGER.debug("Got update: %s", self)

        super()._handle_coordinator_update()
