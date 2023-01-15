"""Support for Xiaomi buttons."""
from __future__ import annotations

import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiButton(XiaomiEntity, ButtonEntity):
    """Representation of Xiaomi button."""

    entity_description: ButtonEntityDescription
    method: Callable

    _attr_device_class = ButtonDeviceClass.RESTART  # TODO: restart?!

    def __init__(self, button, device, entry, coordinator):
        """Initialize the plug switch."""
        self._name = button.name
        unique_id = f"{entry.unique_id}_button_{button.id}"
        self.method = button.method

        super().__init__(device, entry, unique_id, coordinator)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(button.extras.get("entity_category", "config"))
        description = ButtonEntityDescription(
            key=button.id,
            name=button.name,
            icon=button.extras.get("icon"),
            device_class=button.extras.get("device_class"),
            entity_category=category,
        )

        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        await self._try_command(
            f"Failed to execute button {self._name}",
            self.method,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button from a config entry."""
    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    for button in device.actions().values():
        _LOGGER.info("Initializing button: %s", button)
        entities.append(XiaomiButton(button, device, config_entry, coordinator))

    async_add_entities(entities)
