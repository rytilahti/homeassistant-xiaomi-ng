"""Support for Xiaomi Miio binary sensors."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiBinarySensor(XiaomiEntity, BinarySensorEntity):
    """Representation of a Xiaomi Humidifier binary sensor."""

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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi sensor from a config entry."""
    entities: list[XiaomiBinarySensor] = []

    device = hass.data[DOMAIN][config_entry.entry_id].get(KEY_DEVICE)
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]
    for sensor in device.sensors().values():
        if sensor.type == bool:
            # TODO: we might need to rethink this, as some properties (e.g., for mops)
            #       are none depending on the device mode at least for miio devices
            #       maybe these should just default to be disabled?
            if getattr(coordinator.data, sensor.property) is None:
                _LOGGER.debug("Skipping %s as it's value was None", sensor.property)
                continue

            entities.append(
                XiaomiBinarySensor(device, sensor, config_entry, coordinator)
            )

    async_add_entities(entities)
