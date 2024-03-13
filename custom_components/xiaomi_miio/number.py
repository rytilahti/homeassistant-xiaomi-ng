"""Motor speed support for Xiaomi Mi Air Humidifier."""
from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import PropertyConstraint, RangeDescriptor

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiNumber(XiaomiEntity, NumberEntity):
    """Representation of a generic Xiaomi attribute selector."""

    def __init__(
        self,
        device: XiaomiDevice,
        setting: RangeDescriptor,
    ):
        """Initialize the generic Xiaomi attribute selector."""
        # TODO: move setter to the descriptor base class?
        self._setter = setting.setter
        super().__init__(device, setting)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = NumberEntityDescription(
            key=setting.status_attribute,
            name=setting.name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
            native_unit_of_measurement=setting.unit,
            native_min_value=setting.min_value,
            native_max_value=setting.max_value,
            native_step=setting.step,
        )

        _LOGGER.debug("Adding number entity: %s", description)
        self.entity_description = description

    async def async_set_native_value(self, value):
        """Set an option of the miio device."""
        if await self._try_command(
            "Changing setting %s using failed" % self.entity_description.name,
            self._setter,
            int(value),
        ):
            self._attr_native_value = value
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        # On state change the device doesn't provide the new state immediately.
        self._attr_native_value = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Selectors from a config entry."""
    entities = []
    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]

    range_settings = filter(
        lambda x: x.type == PropertyConstraint.Range,
        device.settings(skip_standard=True).values(),
    )
    for setting in range_settings:
        setting = cast(RangeDescriptor, setting)
        _LOGGER.debug("Adding number: %s", setting)
        entities.append(XiaomiNumber(device, setting))

    async_add_entities(entities)
