"""Support for Xiaomi Mi Air Purifier and Xiaomi Mi Air Humidifier."""
from __future__ import annotations

from abc import abstractmethod
import logging
from typing import Any

from homeassistant.components.fan import FanEntity
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    KEY_COORDINATOR,
    KEY_DEVICE,
)
from .device import XiaomiMiioEntity

_LOGGER = logging.getLogger(__name__)

DATA_KEY = "fan.xiaomi_ng"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi vacuum cleaner robot from a config entry."""
    entities = []

    unique_id = config_entry.unique_id

    vacuum = XiaomiFan(
        hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE],
        config_entry,
        unique_id,
        hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR],
    )
    entities.append(vacuum)

    # TODO: add support for custom services (based on actions taking inputs)

    async_add_entities(entities, update_before_add=True)


class XiaomiFan(XiaomiMiioEntity, FanEntity):
    """Representation of a generic Xiaomi device."""

    def __init__(self, device, entry, unique_id, coordinator):
        """Initialize the generic Xiaomi device."""
        super().__init__(device, entry, unique_id, coordinator)

        self._available_attributes = {}
        self._state = None
        self._mode = None
        self._fan_level = None
        self._state_attrs = {}
        self._device_features = 0
        self._preset_modes = []

    @property
    @abstractmethod
    def operation_mode_class(self):
        """Hold operation mode class."""

    @property
    def preset_modes(self) -> list[str]:
        """Get the list of available preset modes."""
        return self._preset_modes

    @property
    def percentage(self) -> int | None:
        """Return the percentage based speed of the fan."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self._state

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the device on."""
        result = await self._try_command(
            "Turning the miio device on failed.", self._device.on
        )

        # If operation mode was set the device must not be turned on.
        if percentage:
            await self.async_set_percentage(percentage)
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)

        if result:
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        result = await self._try_command(
            "Turning the miio device off failed.", self._device.off
        )

        if result:
            self._state = False
            self.async_write_ha_state()
