"""Support led_brightness for Mi Air Humidifier."""
from __future__ import annotations

import logging

from miio.descriptors import SettingType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE, CONF_FLOW_TYPE, DOMAIN, KEY_COORDINATOR, KEY_DEVICE

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from .device import XiaomiMiioEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)


class XiaomiSelect(XiaomiMiioEntity, SelectEntity):
    """Representation of a generic Xiaomi attribute selector."""

    _attr_has_entity_name = True

    def __init__(self, device, setting, entry, coordinator):
        """Initialize the generic Xiaomi attribute selector."""
        self._name = setting.name
        unique_id = f"{entry.unique_id}_select_{setting.id}"
        self._setter = setting.setter

        super().__init__(device, entry, unique_id, coordinator)
        self._choices = setting.choices
        self._attr_current_option = (
            None  # TODO we don't know the value, but the parent wants it?
        )

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        self.entity_description = SelectEntityDescription(
            key=setting.property,
            name=setting.name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
        )
        self._attr_options = [x.name for x in self._choices]

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        value = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        # Sometimes (quite rarely) the device returns None as the LED brightness so we
        # check that the value is not None before updating the state.
        if value is not None:
            try:
                self._attr_current_option = self._choices[value].name
            except ValueError:
                self._attr_current_option = "Unknown"
            finally:
                _LOGGER.debug("Got update: %s", self)
                self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Set an option of the miio device."""
        _LOGGER.debug("Setting select value to: %s", option)
        opt = self._choices[option]
        if await self._try_command(
            "Setting the select value failed",
            self._setter,
            opt.value,
        ):
            self._attr_current_option = option
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Selectors from a config entry."""
    if not config_entry.data[CONF_FLOW_TYPE] == CONF_DEVICE:
        return

    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    for setting in device.settings().values():
        if setting.type == SettingType.Enum:
            _LOGGER.debug("Adding new select: %s", setting)
            entities.append(XiaomiSelect(device, setting, config_entry, coordinator))

    async_add_entities(entities)
