"""Support for Xiaomi Smart WiFi Socket and Smart Power Strip."""

from __future__ import annotations

import logging
from functools import cached_property

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import PropertyDescriptor

from . import XiaomiConfigEntry
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiSwitch(XiaomiEntity, SwitchEntity):
    """Representation of Xiaomi switch."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        device: XiaomiDevice,
        setting: PropertyDescriptor,
    ):
        """Initialize the plug switch."""
        self._setter = setting.setter

        super().__init__(device, setting)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = SwitchEntityDescription(
            key=setting.status_attribute,
            name=self._name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
        )

        _LOGGER.debug("Adding switch: %s", description)
        self.entity_description = description

    @cached_property
    def device_class(self) -> SwitchDeviceClass | None:
        """Return device class.

        The setting-given class is used if available, otherwise fallback
        to detect outlets based on model information.
        """
        if self.entity_description.device_class:
            return self.entity_description.device_class

        # TODO: expose device_type for all Devices.
        # TODO: this should use the device type, not the model string.
        if "switch" in self._device.model:
            return SwitchDeviceClass.OUTLET

        return SwitchDeviceClass.SWITCH

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
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
    config_entry: XiaomiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch from a config entry."""
    entities = []
    device = config_entry.runtime_data.device

    # TODO: we need to handle powerstrips, plugs etc. separately as they are
    #  now skipped completely due to skip_standard

    switches = filter(
        lambda x: x.type is bool, device.settings(skip_standard=True).values()
    )
    for switch in switches:
        _LOGGER.info("Adding switch: %s", switch)
        entities.append(XiaomiSwitch(device, switch))

    async_add_entities(entities)
