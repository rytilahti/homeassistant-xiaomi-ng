"""Support for Xiaomi Philips Lights."""
from __future__ import annotations

import logging
from math import ceil
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .device import XiaomiMiioEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Light"
DATA_KEY = "light.xiaomi_ng"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi light from a config entry."""
    entities: list[LightEntity] = []
    entity: LightEntity

    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    _LOGGER.info("Setting up light platform for %s", device)

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    unique_id = config_entry.unique_id

    # TODO: handle devices with multiple lights
    entity = XiaomiLight(device, config_entry, unique_id, coordinator)
    entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class XiaomiLight(XiaomiMiioEntity, LightEntity):
    """Representation of Xiaomi Light."""

    def __init__(self, device, entry, unique_id, coordinator):
        """Initialize the light device."""
        super().__init__(device, entry, unique_id, coordinator)

        self._brightness = None
        self._available = False
        self._state = None
        self._coordinator = coordinator
        _LOGGER.info("Got light with %s", self._device.settings())

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        # TODO: effect, flash, transition from lightentityfeature
        return super().supported_features

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Return set of supported color modes."""
        modes = set()
        if "light:brightness" in self._device.settings():
            modes.add(ColorMode.BRIGHTNESS)
        if "light:color-temperature" in self._device.settings():
            modes.add(ColorMode.COLOR_TEMP)
        if "light:color" in self._device.settings():
            modes.add(ColorMode.RGB)

        return modes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # TODO: handle different types of turn on
        if ATTR_RGB_COLOR in kwargs:
            _LOGGER.warning("Setting color is not yet implemented")
            return
        elif ATTR_COLOR_TEMP in kwargs:

            _LOGGER.warning("Color temp is not yet implemented")
            # color_temp = kwargs[ATTR_COLOR_TEMP]
            # percent_color_temp = self.translate(
            #    color_temp, self.max_mireds, self.min_mireds, CCT_MIN, CCT_MAX
            # )
            return

        elif ATTR_BRIGHTNESS in kwargs and ATTR_COLOR_TEMP in kwargs:
            _LOGGER.warning(
                "Setting both brightness & colortemp is not yet implemented"
            )
            return

        elif ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent_brightness = ceil(100 * brightness / 255.0)

            _LOGGER.debug("Setting brightness: %s %s%%", brightness, percent_brightness)

            result = await self._try_command(
                "Setting brightness failed: %s",
                self.set_setting,
                "light:brightness",
                percent_brightness,
            )

            if result:
                self._brightness = brightness

        else:
            await self._try_command(
                "Turning the light on failed.", self.set_setting, "light:on", True
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._try_command(
            "Turning the light off failed.", self.set_setting, "light:on", False
        )

    @callback
    def _handle_coordinator_update(self):
        settings = self._device.settings()
        if "light:on" in settings:
            self._attr_is_on = self.get_setting("light:on")
        if "light:brightness" in settings:
            brightness = self.get_setting("light:brightness")
            self._attr_brightness = ceil((255 / 100.0) * brightness)
        _LOGGER.error(f"LIGHT: {self._attr_is_on=} {self._attr_brightness=}")

    @staticmethod
    def translate(value, left_min, left_max, right_min, right_max):
        """Map a value from left span to right span."""
        left_span = left_max - left_min
        right_span = right_max - right_min
        value_scaled = float(value - left_min) / float(left_span)
        return int(right_min + (value_scaled * right_span))
