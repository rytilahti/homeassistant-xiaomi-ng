"""Support led_brightness for Mi Air Humidifier."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import EnumDescriptor, PropertyConstraint

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiSelect(XiaomiEntity, SelectEntity):
    """Representation of a generic Xiaomi attribute selector."""

    def __init__(
        self,
        device: XiaomiDevice,
        setting: EnumDescriptor,
    ):
        """Initialize the generic Xiaomi attribute selector."""
        super().__init__(device, setting)
        self._setter = setting.setter
        self._choices = setting.choices
        self._attr_current_option: str | None = None

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        self.entity_description = SelectEntityDescription(
            key=setting.status_attribute,
            name=setting.name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
        )
        _LOGGER.info("Created %s", self.entity_description)
        if not self._choices:
            _LOGGER.error("No choices found for %s, bug" % setting)
        else:
            self._attr_options = [x.name for x in self._choices]

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        value = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        if value is not None:
            try:
                self._attr_current_option = self._choices(value).name
            except (ValueError, KeyError):
                _LOGGER.error(
                    "Unable to find value %r from %s for %s",
                    value,
                    list(self._choices),
                    self._name,
                )
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
            opt,
        ):
            self._attr_current_option = option
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Selectors from a config entry."""
    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]

    choice_settings = filter(
        lambda x: x.constraint == PropertyConstraint.Choice,
        device.settings(skip_standard=True).values(),
    )
    for setting in choice_settings:
        _LOGGER.debug("Adding new select: %s", setting)
        entities.append(XiaomiSelect(device, setting))

    async_add_entities(entities)
