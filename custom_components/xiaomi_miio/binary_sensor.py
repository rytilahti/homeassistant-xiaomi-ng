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
from miio.descriptors import PropertyDescriptor

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiBinarySensor(XiaomiEntity, BinarySensorEntity):
    """Representation of a Xiaomi Humidifier binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        device: XiaomiDevice,
        sensor: PropertyDescriptor,
    ):
        """Initialize the entity."""
        super().__init__(device, sensor)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(sensor.extras.get("entity_category", "diagnostic"))
        description = BinarySensorEntityDescription(
            key=sensor.status_attribute,
            name=sensor.name,
            icon=sensor.extras.get("icon"),
            device_class=sensor.extras.get("device_class"),
            entity_category=category,
            entity_registry_enabled_default=sensor.extras.get("enabled_default", True),
        )

        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Got update: %s", self)
        self._attr_is_on = bool(
            getattr(self.coordinator.data, self.entity_description.key)
        )

        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi sensor from a config entry."""
    entities: list[XiaomiBinarySensor] = []

    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id].get(KEY_DEVICE)
    sensors = filter(lambda s: s.type == bool, device.sensors().values())
    for sensor in sensors:
        entities.append(XiaomiBinarySensor(device, sensor))

    async_add_entities(entities)
