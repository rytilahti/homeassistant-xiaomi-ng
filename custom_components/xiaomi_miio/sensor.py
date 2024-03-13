"""Support for Xiaomi Mi Air Quality Monitor (PM2.5) and Humidifier."""
from __future__ import annotations

import datetime
import logging
from enum import Enum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from miio.descriptors import PropertyDescriptor

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Sensor"


class XiaomiSensor(XiaomiEntity, SensorEntity):
    """Representation of a Xiaomi generic sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        device: XiaomiDevice,
        sensor: PropertyDescriptor,
    ):
        """Initialize the entity."""
        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(sensor.extras.get("entity_category", "diagnostic"))
        description = SensorEntityDescription(
            key=sensor.status_attribute,
            name=sensor.name,
            native_unit_of_measurement=sensor.unit,
            icon=sensor.extras.get("icon"),
            device_class=sensor.extras.get("device_class"),
            state_class=sensor.extras.get("state_class"),
            entity_category=category,
            entity_registry_enabled_default=sensor.extras.get("enabled_default", True),
        )
        _LOGGER.debug("Adding sensor: %s", description)
        super().__init__(device, sensor)
        self.entity_description = description
        self._attr_native_value = self._determine_native_value()

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        native_value = self._determine_native_value()
        # Sometimes (quite rarely) the device returns None as the sensor value so we
        # check that the value is not None before updating the state.
        _LOGGER.debug("Got update: %s", self)
        if native_value is not None:
            self._attr_native_value = native_value
            self._attr_available = True
            self.async_write_ha_state()

    def _determine_native_value(self):
        """Determine native value."""
        try:
            val = getattr(self.coordinator.data, self.entity_description.key)
        except AttributeError:
            _LOGGER.error(
                "Data with key %s not found but expected: %s",
                self.entity_description.key,
                self.coordinator.data,
            )
            return None

        if isinstance(val, Enum):
            return val.name
        if (
            self.device_class == SensorDeviceClass.TIMESTAMP
            and val is not None
            and (native_datetime := dt_util.parse_datetime(str(val))) is not None
        ):
            return native_datetime.astimezone(dt_util.UTC)
        if isinstance(val, datetime.timedelta):
            return self._parse_time_delta(val)
        if isinstance(val, datetime.time):
            return self._parse_datetime_time(val)
        if isinstance(val, datetime.datetime):
            return self._parse_datetime_datetime(val)

        return val


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi sensor from a config entry."""
    entities: list[SensorEntity] = []
    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    sensors = filter(
        lambda s: s.type != bool, device.sensors(skip_standard=True).values()
    )
    for sensor in sensors:
        entities.append(XiaomiSensor(device, sensor))

    async_add_entities(entities)
