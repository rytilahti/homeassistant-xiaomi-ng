"""Support for Xiaomi Miio switch entities."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from .device import XiaomiMiioEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)


class XiaomiSwitch(XiaomiMiioEntity, SwitchEntity):
    """Representation of Xiaomi switch."""

    entity_description: SwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(self, device, setting, entry, coordinator):
        """Initialize the plug switch."""
        self._name = name = setting.name
        self._property = setting.property
        self._setter = setting.setter
        unique_id = f"{entry.unique_id}_switch_{setting.id}"

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
