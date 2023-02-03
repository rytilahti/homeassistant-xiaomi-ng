"""Motor speed support for Xiaomi Mi Air Humidifier."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from miio import Device
from miio.descriptors import NumberSettingDescriptor, SettingType

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiNumber(XiaomiEntity, NumberEntity):
    """Representation of a generic Xiaomi attribute selector."""

    def __init__(
        self,
        device: Device,
        setting: NumberSettingDescriptor,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
    ):
        """Initialize the generic Xiaomi attribute selector."""
        self._name = setting.name
        unique_id = f"{device.device_id}_number_{setting.id}"
        self._setter = setting.setter

        super().__init__(device, entry, unique_id, coordinator)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = NumberEntityDescription(
            key=setting.property,
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

    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    _LOGGER.info("Going to setup number for %s", device)

    # Handle switches defined by the backing class.
    for setting in device.settings().values():
        if setting.type == SettingType.Number:
            _LOGGER.debug("Adding new number setting: %s", setting)
            entities.append(XiaomiNumber(device, setting, config_entry, coordinator))

    async_add_entities(entities)
