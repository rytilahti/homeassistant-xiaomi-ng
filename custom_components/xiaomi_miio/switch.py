"""Support for Xiaomi Smart WiFi Socket and Smart Power Strip."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from miio import Device
from miio.descriptors import SettingDescriptor, SettingType

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Switch"
DATA_KEY = "switch.xiaomi_miio"


class XiaomiSwitch(XiaomiEntity, SwitchEntity):
    """Representation of Xiaomi switch."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        device: Device,
        setting: SettingDescriptor,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
    ):
        """Initialize the plug switch."""
        self._name = name = setting.name
        self._property = setting.property
        self._setter = setting.setter
        unique_id = f"{device.device_id}_switch_{setting.id}"

        super().__init__(device, entry, unique_id, coordinator)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = SwitchEntityDescription(
            key=setting.property,
            name=name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
        )

        _LOGGER.debug("Adding switch: %s", description)

        self._attr_is_on = self._extract_value_from_attribute(
            self.coordinator.data, description.key
        )
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        # On state change the device doesn't provide the new state immediately.
        self._attr_is_on = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on an option of the miio device."""
        if await self._try_command("Turning %s on failed", self._setter, True):
            # Write state back to avoid switch flips with a slow response
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off an option of the miio device."""
        if await self._try_command("Turning off failed", self._setter, False):
            # Write state back to avoid switch flips with a slow response
            self._attr_is_on = False
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch from a config entry."""

    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    # TODO: special handling for switch devices

    switches = filter(
        lambda x: x.type == SettingType.Boolean, device.settings().values()
    )
    for switch in switches:
        _LOGGER.info("Adding switch: %s", switch)
        entities.append(XiaomiSwitch(device, switch, config_entry, coordinator))

    async_add_entities(entities)
