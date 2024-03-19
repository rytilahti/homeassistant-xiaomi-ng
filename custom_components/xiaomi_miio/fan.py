"""Support for Xiaomi Philips Lights."""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import EnumDescriptor
from miio.identifiers import FanId

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi light from a config entry."""
    entities: list[FanEntity] = []

    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    _LOGGER.info("Setting up fan platform for %s", device)

    entity = XiaomiFan(device)
    entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class XiaomiFan(XiaomiEntity, FanEntity):
    """Representation of Xiaomi Light."""

    def __init__(self, device: XiaomiDevice):
        """Initialize the light device."""
        super().__init__(device)

        self._state = None

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return supported features."""
        features = FanEntityFeature(0)
        if self._device.get(FanId.Speed):
            features |= FanEntityFeature.SET_SPEED
        if self._device.get(FanId.Oscillate):
            features |= FanEntityFeature.OSCILLATE
        # TODO: disabled in favor of more generic angle option
        if self._device.get(FanId.Angle):
            features |= FanEntityFeature.DIRECTION
        if self._device.get(FanId.Preset):
            features |= FanEntityFeature.PRESET_MODE

        return features

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        if percentage is not None:
            await self._try_command(
                "Turning the fan on with percentage failed.",
                self.set_property,
                FanId.Speed,
                percentage,
            )

        if preset_mode is not None:
            await self._try_command(
                "Turning the fan preset mode failed.",
                self.set_property,
                FanId.Preset,
                preset_mode,
            )

        await self._try_command(
            "Turning the fan on failed.", self.set_property, FanId.On, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self._try_command(
            "Turning the fan off failed.", self.set_property, FanId.On, False
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed."""
        # TODO: devdocs: Manually setting a speed must disable any set preset mode.
        #  If it is possible to set a percentage speed manually without disabling
        #  the preset mode, create a switch or service to represent the mode.
        return await self._try_command(
            "Setting percentage failed.", self.set_property, FanId.Speed, percentage
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        return await self._try_command(
            "Setting preset mode failed.",
            self.set_property,
            FanId.Preset,
            preset_mode,
        )

    async def async_set_direction(self, direction: str) -> None:
        """Set direction."""
        return await self._try_command(
            "Setting direction failed.", self.set_property, FanId.Angle, direction
        )

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillating."""
        return await self._try_command(
            "Setting oscillate failed.",
            self.set_property,
            FanId.Oscillate,
            oscillating,
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.get_value(FanId.On)
        if self.supported_features & FanEntityFeature.SET_SPEED:
            self._attr_percentage = self.get_value(FanId.Speed)
        if self.supported_features & FanEntityFeature.OSCILLATE:
            self._attr_oscillating = self.get_value(FanId.Oscillate)

        # TODO: is speed count anymore relevant, shouldn't that be deprecated by now?
        # TODO: update the homeassistant docs accordingly
        # self._attr_speed_count = self.get_value(FanId.SpeedCount)

        # TODO: find a better way to work on enums
        if self.supported_features & FanEntityFeature.PRESET_MODE:
            preset = self.get_descriptor(FanId.Preset)
            preset = cast(EnumDescriptor, preset)
            self._attr_preset_mode = preset.choices(self.get_value(FanId.Preset)).name
            self._attr_preset_modes = list(preset.choices._member_map_.keys())

        # TODO: find a better way to work on enums
        if self.supported_features & FanEntityFeature.DIRECTION:
            angles = self.get_descriptor(FanId.Angle)
            angles = cast(EnumDescriptor, angles)
            self._attr_current_direction = angles.choices(
                self.get_value(FanId.Angle)
            ).name

        super()._handle_coordinator_update()
