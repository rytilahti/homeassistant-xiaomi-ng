"""Support for Xiaomi buttons."""

from __future__ import annotations

import logging
from typing import Callable

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import ActionDescriptor

from . import XiaomiConfigEntry
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


class XiaomiButton(XiaomiEntity, ButtonEntity):
    """Representation of Xiaomi button."""

    entity_description: ButtonEntityDescription
    method: Callable

    _attr_device_class = ButtonDeviceClass.RESTART  # TODO: check the type

    def __init__(
        self,
        device: XiaomiDevice,
        button: ActionDescriptor,
    ):
        """Initialize the plug switch."""
        # TODO: should both name and method be stored inside the entity description?
        self._method = button.method

        super().__init__(device, button)

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(button.extras.get("entity_category", "config"))
        # TODO: check what the key should be, for readables this is state_attribute
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
            self._method,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: XiaomiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button from a config entry."""
    entities = []
    device = config_entry.runtime_data.device

    for button in device.actions(skip_standard=True).values():
        _LOGGER.info("Initializing button: %s", button)
        entities.append(XiaomiButton(device, button))

    async_add_entities(entities)
