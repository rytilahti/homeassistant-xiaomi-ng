"""Support for Xiaomi Mi Air Quality Monitor (PM2.5) and Humidifier."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .ng_sensor import XiaomiSensor

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Sensor"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi sensor from a config entry."""
    entities: list[SensorEntity] = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    for sensor in device.sensors().values():
        if sensor.type != bool:
            if getattr(coordinator.data, sensor.property) is None:
                # TODO: we might need to rethink this, as some properties (e.g., mops)
                #       are none depending on the device mode at least for miio devices
                #       maybe these should just default to be disabled?
                _LOGGER.debug("Skipping %s as it's value was None", sensor.property)
                continue

            entities.append(XiaomiSensor(device, sensor, config_entry, coordinator))

    async_add_entities(entities)
