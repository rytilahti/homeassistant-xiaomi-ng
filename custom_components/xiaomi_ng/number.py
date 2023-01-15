"""Motor speed support for Xiaomi Mi Air Humidifier."""
from __future__ import annotations

import logging

from miio.descriptors import SettingType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from .device import XiaomiMiioEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory


_LOGGER = logging.getLogger(__name__)


class XiaomiNumber(XiaomiMiioEntity, NumberEntity):
    """Representation of a generic Xiaomi attribute selector."""

    def __init__(self, device, setting, entry, coordinator):
        """Initialize the generic Xiaomi attribute selector."""
        self._name = setting.name
        unique_id = f"{entry.unique_id}_number_{setting.id}"
        self._setter = setting.setter

        super().__init__(device, entry, unique_id, coordinator)

        self._attr_native_value = self._extract_value_from_attribute(
            coordinator.data, setting.id
        )

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = NumberEntityDescription(
            key=setting.id,
            name=setting.name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
            native_unit_of_measurement=setting.unit,
            native_min_value=setting.min_value,
            native_max_value=setting.max_value,
            native_step=setting.step,
        )

        self.entity_description = description

    async def async_set_native_value(self, value):
        """Set an option of the miio device."""
        if await self._try_command(
            "Turning %s on failed", self._setter, value=int(value)
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

    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    _LOGGER.info("Going to setup number for %s", device)

    # Handle switches defined by the backing class.
    for setting in device.settings().values():
        if setting.type == SettingType.Number:
            _LOGGER.debug("Adding new number setting: %s", setting)
            entities.append(XiaomiNumber(device, setting, config_entry, coordinator))

    async_add_entities(entities)
