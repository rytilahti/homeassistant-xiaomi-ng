"""Support for Xiaomi Lights."""
from __future__ import annotations

import logging
from math import ceil
from typing import Any, cast

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import RangeDescriptor
from miio.identifiers import LightId

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


def convert_rgb_to_int(rgb: tuple[int, int, int]) -> int:
    """Convert rgb tuple to int presentation."""
    return (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]


def convert_int_to_rgb(rgb: int | None) -> tuple[int, int, int] | None:
    """Convert int to rgb tuple."""
    if rgb is None:
        return None
    return (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi light from a config entry."""
    entities: list[LightEntity] = []

    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    _LOGGER.info("Setting up light platform for %s", device)

    # TODO: handle devices with multiple lights
    entity = XiaomiLight(device)
    entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class XiaomiLight(XiaomiEntity, LightEntity):
    """Representation of Xiaomi Light."""

    def __init__(self, device: XiaomiDevice):
        """Initialize the light device."""
        super().__init__(device)
        self._state = None

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        # TODO: need to way to signal about transitions being supported
        return super().supported_features

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str]:
        """Return set of supported color modes."""
        modes = set()

        # TODO: this should be cached

        if self._device.get(LightId.ColorTemperature):
            modes.add(ColorMode.COLOR_TEMP)

        if self._device.get(LightId.Color):
            modes.add(ColorMode.RGB)

        # If device does not support colortemp nor rgb,
        # it's either brightness only or on/off
        if not modes:
            if self._device.get(LightId.Brightness):
                modes.add(ColorMode.BRIGHTNESS)
            else:
                _LOGGER.debug("No color modes for %s, assuming on/off", self._device)
                modes.add(ColorMode.ONOFF)

        _LOGGER.debug(
            "Got color modes for %s: %s",
            self._device,
            modes,
        )

        return modes

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self.get_value(LightId.ColorTemperature)

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the minimum color temperature in Kelvin."""
        ct_prop = cast(RangeDescriptor, self._device.get(LightId.ColorTemperature))
        return ct_prop.min_value

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the maximum color temperature in Kelvin."""
        ct_prop = cast(RangeDescriptor, self._device.get(LightId.ColorTemperature))
        return ct_prop.max_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent_brightness = ceil(100 * brightness / 255.0)

            _LOGGER.debug("Setting brightness: %s %s%%", brightness, percent_brightness)

            return await self._try_command(
                "Setting brightness failed: %s",
                self.set_property,
                LightId.Brightness,
                percent_brightness,
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            _LOGGER.debug("Setting color temperature: %s", color_temp)
            return await self._try_command(
                "Setting color temperature failed: %s",
                self.set_property,
                LightId.ColorTemperature,
                color_temp,
            )

        if ATTR_RGB_COLOR in kwargs:
            rgb_color = kwargs[ATTR_RGB_COLOR]
            _LOGGER.warning("Setting rgb color: %s", rgb_color)
            return await self._try_command(
                "Setting rgb color failed: %s",
                self.set_property,
                LightId.Color,
                convert_rgb_to_int(rgb_color),
            )

        await self._try_command(
            "Turning the light on failed.", self.set_property, LightId.On, True
        )
        return None

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._try_command(
            "Turning the light off failed.", self.set_property, LightId.On, False
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return the current color mode."""
        if len(self.supported_color_modes) == 1:
            # The light is either on/off or brightness only
            return list(self.supported_color_modes)[0]
        if self._attr_rgb_color:
            return ColorMode.RGB
        if self._attr_color_temp_kelvin:
            return ColorMode.COLOR_TEMP

        return ColorMode.BRIGHTNESS

    @callback
    def _handle_coordinator_update(self):
        self._attr_is_on = self.get_value(LightId.On)
        brightness = self.get_value(LightId.Brightness)
        if brightness is not None:
            self._attr_brightness = ceil((255 / 100.0) * brightness)

        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            self._attr_color_temp_kelvin = self.get_value(LightId.ColorTemperature)

        if ColorMode.RGB in self.supported_color_modes:
            self._attr_rgb_color = convert_int_to_rgb(self.get_value(LightId.Color))

        super()._handle_coordinator_update()
